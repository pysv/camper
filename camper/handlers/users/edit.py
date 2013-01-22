#encoding=utf8
from starflyer import Handler, redirect
from camper import BaseForm, db, BaseHandler
from camper import logged_in, is_admin
from wtforms import *
from camper.handlers.forms import *
import werkzeug.exceptions

TSHIRT_CHOICES = (
    ('s' , 'S'),
    ('m' , 'M'),
    ('l' , 'L'),
    ('xl' , 'XL'),
    ('xxl' , 'XXL'),
)

class EditForm(BaseForm):
    """form for adding a barcamp"""
    fullname      = TextField(u"Voller Name")
    bio           = TextAreaField(u"Über mich", description = u'Schreibe etwas über Dich',)
    organisation  = TextField(u"Organisation", [validators.Length(max=100)], description = "Deine Schule, Verein etc. (max. 100 Zeichen)")
    twitter       = TextField(u"Twitter-Name", [validators.Length(max=100)], description = "bitte nur Deinen Usernamen angeben")
    facebook      = TextField(u"Facebook", [validators.Length(max=255)], description = "Link zu Deinem Facebook-Profil")
    tshirt        = SelectField(u"T-Shirt-Größe", choices = TSHIRT_CHOICES)
    image         = UploadField(u"Bild")

class ProfileEditView(BaseHandler):
    """shows the profile edit form"""

    template = "users/edit.html"

    def get(self):
        """render the view"""
        form = EditForm(self.request.form, obj = self.user, config = self.config)
        if self.request.method=="POST":
            if form.validate():
                self.user.update(form.data)
                self.user.save()
                self.flash("Dein Profil wurde aktualisiert", category="info")
                url = self.url_for("profile", username = self.user.username)
                return redirect(url)
            else:
                self.flash("Leider enthielt das Formular einen Fehler", category="error")
        return self.render(form = form)

    post = get

class ProfileImageDeleteView(BaseHandler):
    """delete the profile image"""

    @logged_in()
    def delete(self):
        """delete the profile image and return to the profile page"""
        asset_id = self.user.image
        if asset_id is not None:
            asset = self.app.module_map.uploader.remove(asset_id)
            self.user.image = None
            self.user.save()
            self.flash(self._("Your profile image has been deleted"), category="info")
        url = self.url_for("profile", username = self.user.username)
        return redirect(url)
