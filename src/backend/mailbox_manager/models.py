"""
Declare and configure the models for the People additional application : mailbox_manager
"""

import smtplib
from logging import getLogger

from django.conf import settings
from django.contrib.sites.models import Site
from django.core import exceptions, mail, validators
from django.db import models
from django.template.loader import render_to_string
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from rest_framework import status

from core.models import BaseModel

from mailbox_manager.enums import MailDomainRoleChoices, MailDomainStatusChoices
from mailbox_manager.utils.dimail import DimailAPIClient

logger = getLogger(__name__)


class MailDomain(BaseModel):
    """Domain names from which we will create email addresses (mailboxes)."""

    name = models.CharField(
        _("name"), max_length=150, null=False, blank=False, unique=True
    )
    slug = models.SlugField(null=False, blank=False, unique=True, max_length=80)
    status = models.CharField(
        max_length=10,
        default=MailDomainStatusChoices.PENDING,
        choices=MailDomainStatusChoices.choices,
    )

    class Meta:
        db_table = "people_mail_domain"
        verbose_name = _("Mail domain")
        verbose_name_plural = _("Mail domains")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Override save function to compute the slug."""
        self.slug = self.get_slug()
        return super().save(*args, **kwargs)

    def get_slug(self):
        """Compute slug value from name."""
        return slugify(self.name)

    def get_abilities(self, user):
        """
        Compute and return abilities for a given user on the domain.
        """
        is_owner_or_admin = False
        role = None

        if user.is_authenticated:
            try:
                role = self.accesses.filter(user=user).values("role")[0]["role"]
            except (MailDomainAccess.DoesNotExist, IndexError):
                role = None

        is_owner_or_admin = role in [
            MailDomainRoleChoices.OWNER,
            MailDomainRoleChoices.ADMIN,
        ]

        return {
            "get": bool(role),
            "patch": is_owner_or_admin,
            "put": is_owner_or_admin,
            "post": is_owner_or_admin,
            "delete": role == MailDomainRoleChoices.OWNER,
            "manage_accesses": is_owner_or_admin,
        }


class MailDomainAccess(BaseModel):
    """Allow to manage users' accesses to mail domains."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mail_domain_accesses",
        null=False,
        blank=False,
    )
    domain = models.ForeignKey(
        MailDomain,
        on_delete=models.CASCADE,
        related_name="accesses",
        null=False,
        blank=False,
    )
    role = models.CharField(
        max_length=20,
        choices=MailDomainRoleChoices.choices,
        default=MailDomainRoleChoices.VIEWER,
    )

    class Meta:
        db_table = "people_mail_domain_accesses"
        verbose_name = _("User/mail domain relation")
        verbose_name_plural = _("User/mail domain relations")
        unique_together = ("user", "domain")

    def __str__(self):
        return f"Access of user {self.user} on domain {self.domain}."


class Mailbox(BaseModel):
    """Mailboxes for users from mail domain."""

    first_name = models.CharField(max_length=200, blank=False)
    last_name = models.CharField(max_length=200, blank=False)
    local_part = models.CharField(
        _("local_part"),
        max_length=150,
        null=False,
        blank=False,
        validators=[validators.RegexValidator(regex="^[a-zA-Z0-9_.-]+$")],
    )
    domain = models.ForeignKey(
        MailDomain,
        on_delete=models.CASCADE,
        related_name="mail_domain",
        null=False,
        blank=False,
    )
    secondary_email = models.EmailField(
        _("secondary email address"), null=False, blank=False
    )

    class Meta:
        db_table = "people_mail_box"
        verbose_name = _("Mailbox")
        verbose_name_plural = _("Mailboxes")
        unique_together = ("local_part", "domain")

    def __str__(self):
        return f"{self.local_part!s}@{self.domain.name:s}"

    def clean(self):
        """
        Mailboxes can only be created on enabled domains.
        Also, mail-provisioning API credentials must be set for dimail to allow auth.
        """
        if self.domain.status != MailDomainStatusChoices.ENABLED:
            raise exceptions.ValidationError(
                "You can create mailbox only for a domain enabled"
            )

        # Won't be able to query user token if MAIL_PROVISIONING_API_CREDENTIALS are not set
        if not settings.MAIL_PROVISIONING_API_CREDENTIALS:
            raise exceptions.ValidationError(
                "Please configure MAIL_PROVISIONING_API_CREDENTIALS before creating any mailbox."
            )

    def save(self, *args, **kwargs):
        """
        Override save function to fire a request on mailbox creation.
        Modification is forbidden for now.
        """
        self.full_clean()

        if self._state.adding:
            # send new mailbox request to dimail
            client = DimailAPIClient()
            response = client.send_mailbox_request(self)

            if response.status_code == status.HTTP_201_CREATED:
                super().save(*args, **kwargs)

            logger.info("Succesfully created email %s.", response.json()["email"])

            self.send_new_mailbox_notification(
                recipient=self.secondary_email,
                mailbox_data={key: response.json()[key] for key in ["email", "password"]}
            )

        # Update is not implemented for now
        raise NotImplementedError()

    def send_new_mailbox_notification(self, recipient, mailbox_data):
        """
        Send email to confirm mailbox creation
        and send new mailbox information.
        """

        template_vars = {
            "title": _("Your new mailbox information"),
            "site": Site.objects.get_current(),
            "webmail_url": settings.WEBMAIL_URL,
            "mailbox_data": mailbox_data,
        }

        msg_html = render_to_string("mail/html/new_mailbox.html", template_vars)
        msg_plain = render_to_string("mail/text/new_mailbox.txt", template_vars)

        try:
            mail.send_mail(
                _("Your new mailbox information"),
                msg_plain,
                settings.EMAIL_FROM,
                [recipient],
                html_message=msg_html,
                fail_silently=False,
            )
            logger.info(
                "Mailbox information for %s sent to %s.", mailbox_data.email, recipient
            )
        except smtplib.SMTPException as exception:
            logger.error(
                "Mailbox confirmation email to %s was not sent: %s",
                recipient,
                exception,
            )
