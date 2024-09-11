"""
Unit tests for the mailbox API
"""

from django.conf import settings
from django.test.utils import override_settings

import pytest
from rest_framework.test import APIClient

from mailbox_manager import enums, factories
from mailbox_manager.api import serializers

pytestmark = pytest.mark.django_db


@override_settings(MAIL_PROVISIONING_API_CREDENTIALS="wrongCredentials")
def test_dimail__wrong_token_permission_denied():
    """
    Dimail should return a 'Permission denied' token denied error
    when faced with an incorrect regie credentials.
    """
    access = factories.MailDomainAccessFactory(role=enums.MailDomainRoleChoices.OWNER)

    client = APIClient()
    client.force_login(access.user)
    body_values = serializers.MailboxSerializer(
        factories.MailboxFactory.build(domain=access.domain)
    ).data

    assert settings.MAIL_PROVISIONING_API_URL == "http://host.docker.internal:8001"
    response = client.post(
        f"/api/v1.0/mail-domains/{access.domain.slug}/mailboxes/",
        body_values,
        format="json",
    )

    # dimail container should return a token denied error
    assert response.json() == {
        "detail": "Token denied. Please check your MAIL_PROVISIONING_API_CREDENTIALS."
    }
