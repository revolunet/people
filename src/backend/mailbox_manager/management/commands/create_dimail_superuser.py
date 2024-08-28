"""Management command creating a super user for dimail-api container, for test purposes."""

from django.core.management.base import BaseCommand

import requests
from rest_framework import status

DIMAIL_ADMIN_USERNAME = "la_regie"
DIMAIL_ADMIN_PASSWORD = "password"  # noqa: S105


class Command(BaseCommand):
    """
    Management command to create a super in from a username and a password for test purposes.
    """

    help = "Create a superuser in dimail-api, for test purposes"

    def handle(self, *args, **options):
        """
        Create a first superuser for dimail-api container. User creation is usually
        protected behind admin rights but dimail allows to create a user when database is empty
        """
        response = requests.post(
            url="http://host.docker.internal:8001/users",
            headers={
                "accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": "Basic Og==",
            },
            json={
                "name": DIMAIL_ADMIN_USERNAME,
                "password": DIMAIL_ADMIN_PASSWORD,
                "is_admin": True,
            },
            timeout=10,
        )
        if response.status_code == status.HTTP_201_CREATED:
            self.stdout.write(self.style.SUCCESS("SUPER"))
        elif response.status_code == status.HTTP_403_FORBIDDEN:
            self.stdout.write(
                self.style.ERROR(
                    "Could not create first admin user, db already populated."
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"An unexpected error occurred: {response.content.decode('utf-8')}"
                )
            )
