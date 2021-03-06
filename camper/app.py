# coding=utf-8

import pymongo
import yaml
import pkg_resources

from starflyer import Application, URL, AttributeMapper
from sfext.uploader import upload_module, Assets, ImageSizeProcessor
from sfext.uploader.stores import FilesystemStore
from sfext.babel import babel_module, T
from sfext.mail import mail_module

import markdown
import bleach

import re
from jinja2 import evalcontextfilter, Markup, escape
from etherpad_lite import EtherpadLiteClient

import userbase
import handlers
import db
import login

#
# custom jinja filters
#


_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')
_striptags_re = re.compile(r'(<!--.*?-->|<[^>]*>)')

@evalcontextfilter
def nl2br(eval_ctx, value):
    value = _striptags_re.sub(' ', value)
    result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', '<br>\n')
                      for p in _paragraph_re.split(escape(value)))
    if eval_ctx.autoescape:
        result = Markup(result)
    return result

def do_currency(value, currency=u"€"):
    """format currency aware"""
    return u'{0:.2f} {1}'.format(value, currency).replace(".",",")

try:
    import simplejson as json
except ImportError:
    import json

if '\\/' not in json.dumps('/'):

    def _tojson_filter(*args, **kwargs):
        return json.dumps(*args, **kwargs).replace('/', '\\/')
else:
    _tojson_filter = json.dumps

def markdownify(text, level=1):
    return bleach.linkify(markdown.markdown(text, safe_mode="remove", extensions=['nl2br', 'headerid(level=%s)' %level]))

###
### i18n
###

def get_locale(handler):
    return "de" # for now

### 
### APP
###

class CamperApp(Application):
    """application"""

    defaults = {
        'log_name'              : "camper",
        'script_virtual_host'   : "http://localhost:8222",
        'virtual_host'          : "http://localhost:8222",
        'virtual_path'          : "",
        'server_name'           : "dev.localhost:9008",
        'title'                 : "Camper - Barcamp Tools",
        'description'           : "barcamp tool",
        'debug'                 : False,
        'mongodb_name'          : "camper",
        'mongodb_port'          : 27017,
        'mongodb_host'          : "localhost",
        'secret_key'            : "7cs687cds6c786cd89&%$%&hhhs8c7zcbs87ct d7stc 8c7cs8 78 7dts 8cs97tugjgjzGUZGUzgcdcg&%%$",
        'session_cookie_domain' : "dev.localhost",
        'smtp_host'             : 'localhost',
        'smtp_port'             : 25,
        'from_addr'             : "noreply@example.org",
        'from_name'             : "Barcamp-Tool",
        'ep_api_key'            : "please fill in from APIKEY.txt",
        'ep_endpoint'           : "http://localhost:9001/api",
        'ga'                    : 'none', #GA key
        'base_asset_path'       : '/tmp', # where to store assets
        'fb_app_id'             : 'PLEASE FILL IN', # get this from developers.facebook.com
    }

    modules = [
        babel_module(
            locale_selector_func = get_locale,
        ),
        userbase.username_userbase(
            url_prefix                  = "/users",
            mongodb_name                = "camper",
            master_template             = "master.html",
            login_after_registration    = True,
            double_opt_in               = True,
            enable_registration         = True,
            enable_usereditor           = True,
            user_class                  = db.CamperUser,
            use_remember                = True,
            login_form                  = login.UsernameLoginForm,
            urls                        = {
                'activation'            : {'endpoint' : 'userbase.activate'},
                'activation_success'    : {'endpoint' : 'index'},
                'activation_code_sent'  : {'endpoint' : 'userbase.activate'},
                'login_success'         : {'endpoint' : 'index'},
                'logout_success'        : {'endpoint' : 'userbase.login'},
                'registration_success'  : {'endpoint' : 'userbase.login'},
            },
            messages                    = AttributeMapper({
                'user_unknown'          : T('User unknown'),
                'email_unknown'         : T('This email address cannot not be found in our user database'),
                'password_incorrect'    : T('Your password is not correct'),
                'user_not_active'       : T('Your user has not yet been activated.'), # maybe provide link here? Needs to be constructed in handler
                'login_failed'          : T('Login failed'),
                'login_success'         : T('Welcome, %(fullname)s'),
                'logout_success'        : T('Your are now logged out'),
                'double_opt_in_pending' : T('To finish the registration process please check your email with instructions on how to activate your account.'),
                'registration_success'  : T('Your user registration has been successful'),
                'activation_success'    : T('Your account has been activated'),
                'activation_failed'     : T('The activation code is not valid. Please try again or click <a href="%(url)s">here</a> to get a new one.'),
                'activation_code_sent'  : T('A new activation code has been sent out, please check your email'),
                'already_active'        : T('The user is already active. Please log in.'),
                'pw_code_sent'          : T('A link to set a new password has been sent to you'),
                'pw_changed'            : T('Your password has been changed'),
                
                # for user manager
                'user_edited'           : T('The user has been updated.'),
                'user_added'            : T('The user has been added.'),
                'user_deleted'          : T('The user has been deleted.'),
                'user_activated'        : T('The user has been activated.'),
                'user_deactivated'      : T('The user has been deactivated.'),
            }),

            permissions                 = AttributeMapper({
                'userbase:admin'    : T("can manage users"),
                'admin'             : T("main administrator"),
            })
        ),
        mail_module(debug=True),
    ]

    jinja_filters = {
        'nl2br' : nl2br,
        'currency' : do_currency,
        'tojson' : _tojson_filter,
        'md' : markdownify,
    }

    routes = [
        URL('/', 'index', handlers.index.IndexView),
        URL('/impressum.html', 'impressum', handlers.index.Impressum),
        URL('/', 'root', handlers.index.IndexView),
        URL('/', 'login', handlers.index.IndexView),
        URL('/assets/', 'asset_upload', handlers.images.AssetUploadView),
        URL('/assets/<asset_id>', 'asset', handlers.images.AssetView),

        # admin area 
        URL('/admin/', "admin_index", handlers.admin.index.IndexView),
        URL('/admin/pages', "admin_pages", handlers.admin.pages.PagesView),
        URL('/admin/pages/<slot>/add', 'admin_pages_add', handlers.pages.add.AddView),
        URL('/s/<page_slug>', 'page', handlers.pages.view.View),

        # user stuff
        URL('/u/<username>', 'profile', handlers.users.profile.ProfileView),
        URL('/u/image_delete', 'profile_image_delete', handlers.users.edit.ProfileImageDeleteView),
        URL('/u/edit', 'profile_edit', handlers.users.edit.ProfileEditView),

        # barcamp stuff
        URL('/b/add', 'barcamp_add', handlers.barcamp.add.AddView),
        URL('/b/validate', 'barcamp_validate', handlers.barcamp.add.ValidateView, defaults = {'slug' : None}),
        URL('/<slug>', 'barcamp', handlers.barcamp.index.View),
        URL('/<slug>/validate', 'barcamp_validate', handlers.barcamp.add.ValidateView),
        URL('/<slug>/delete', 'barcamp_delete', handlers.barcamp.delete.DeleteConfirmView),
        URL('/<slug>/edit', 'barcamp_edit', handlers.barcamp.edit.EditView),
        URL('/<slug>/participants_edit', 'barcamp_participants_edit', handlers.barcamp.edit.ParticipantsEditView),
        URL('/<slug>/sponsors', 'barcamp_sponsors', handlers.barcamp.index.BarcampSponsors),
        URL('/<slug>/location', 'barcamp_location', handlers.barcamp.location.LocationView),
        URL('/<slug>/subscribe', 'barcamp_subscribe', handlers.barcamp.registration.BarcampSubscribe),
        URL('/<slug>/register', 'barcamp_register', handlers.barcamp.registration.BarcampRegister),
        URL('/<slug>/unregister', 'barcamp_unregister', handlers.barcamp.registration.BarcampUnregister),
        URL('/<slug>/planning', 'barcamp_planning_pad', handlers.barcamp.pads.PlanningPadView),
        URL('/<slug>/planning/toggle', 'barcamp_planning_pad_toggle', handlers.barcamp.pads.PadPublicToggleView),
        URL('/<slug>/docpad', 'barcamp_documentation_pad', handlers.barcamp.pads.DocumentationPadView),
        URL('/<slug>/lists', 'barcamp_userlist', handlers.barcamp.userlist.UserLists),
        URL('/<slug>/tweetwally', 'barcamp_tweetwally', handlers.barcamp.tweetwally.TweetWallyView),
        URL('/<slug>/permissions', 'barcamp_permissions', handlers.barcamp.permissions.Permissions),
        URL('/<slug>/permissions/admin', 'barcamp_admin', handlers.barcamp.permissions.Admin),
        URL('/<slug>/sessions', 'barcamp_sessions', handlers.barcamp.sessions.SessionList),
        URL('/<slug>/sessions.xls', 'barcamp_session_export', handlers.barcamp.sessions.SessionExport),
        URL('/<slug>/sessions/<sid>', 'barcamp_session', handlers.barcamp.sessions.SessionHandler),
        URL('/<slug>/sessions/<sid>/vote', 'barcamp_session_vote', handlers.barcamp.sessions.Vote),
        URL('/<slug>/sessions/<sid>/comments', 'barcamp_session_comments', handlers.barcamp.sessions.CommentHandler),
        URL('/<slug>/logo/upload', 'barcamp_logo_upload', handlers.barcamp.images.LogoUpload),
        URL('/<slug>/logo/delete', 'barcamp_logo_delete', handlers.barcamp.images.LogoDelete),
        URL('/<slug>/logo', 'barcamp_logo', handlers.barcamp.images.Logo),

        # pages for barcamps
        URL('/<slug>/page_add/<slot>', 'barcamp_page_add', handlers.pages.add.AddView),
        URL('/<slug>/<page_slug>', 'barcamp_page', handlers.pages.view.View),
        URL('/<slug>/<page_slug>/upload', 'page_image_upload', handlers.pages.images.ImageUpload),
        URL('/<slug>/<page_slug>/layout', 'page_layout', handlers.pages.edit.LayoutView),
        URL('/<slug>/<page_slug>/edit', 'page_edit', handlers.pages.edit.EditView),
        URL('/<slug>/<page_slug>/partial_edit', 'page_edit_partial', handlers.pages.edit.PartialEditView),
        URL('/<slug>/<page_slug>/delete', 'page_image_delete', handlers.pages.images.ImageDelete),
        URL('/<slug>/<page_slug>/image', 'page_image', handlers.pages.images.Image),

    ]

    def finalize_setup(self):
        """do our own configuration stuff"""
        self.config.dbs = AttributeMapper()
        mydb = self.config.dbs.db = pymongo.Connection(
            self.config.mongodb_host,
            self.config.mongodb_port
        )[self.config.mongodb_name]
        self.config.dbs.barcamps = db.Barcamps(mydb.barcamps, app=self, config=self.config)
        self.config.dbs.sessions = db.Sessions(mydb.sessions, app=self, config=self.config)
        self.config.dbs.pages = db.Pages(mydb.pages, app=self, config=self.config)
        self.config.dbs.session_comments = db.Comments(mydb.session_comments, app=self, config=self.config)
        self.module_map.uploader.config.assets = Assets(mydb.assets, app=self, config=self.config)

        # etherpad connection
        self.config.etherpad = EtherpadLiteClient(
            base_params={'apikey': self.config.ep_api_key},
            base_url=self.config.ep_endpoint
        )

    def finalize_modules(self):
        """finalize all modules"""
        fsstore = FilesystemStore(base_path = self.config.base_asset_path)
        self.modules.append(upload_module(store = fsstore,
            processors = [
                ImageSizeProcessor({
                    'thumb' : "50x50!",
                    'small' : "100x",
                    'logo_full' : "940x",
                    'medium_user' : "296x",
                    'large' : "1200x",
                })
            ],
        ))

def app(config, **local_config):
    """return the config""" 
    return CamperApp(__name__, local_config)

