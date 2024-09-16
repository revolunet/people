"""Management command creating a  dimail-api container, for test purposes."""

import base64

from django.conf import settings
from django.core.management.base import BaseCommand

import requests
from rest_framework import status

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"  # noqa: S105
REGIE_USERNAME = "regie"
REGIE_PASSWORD = "password"  # noqa: S105
DIMAIL_URL = "http://localhost:8001/"


class Command(BaseCommand):
    """
    Management command populate local dimail database, to ease dev
    """

    help = "Populate local dimail database, for dev purposes."

    def handle(self, *args, **options):
        """Handling of the management command."""
        if not settings.DEBUG:
            raise CommandError(
                ("This command is meant to run in local dev environment.")
            )

        # create first admin user in empty database
        self.create_admin_user()

        self.create_regie_user()
        # except:
        #     self.stdout.write(
        #         self.style.ERROR(
        #             f"SOMETHING FAILED"
        #         ))
        # else:
        #     self.stdout.write(
        #         self.style.SUCCESS(
        #             f"Succesfully populated local dimail !"
        #         ))

        # We should never reach this part of the code.
        self.stdout.write(
            self.style.ERROR(
                f"An unexpected error occurred: {response.content.decode('utf-8')}"
            )
        )
        return 1

    def create_admin_user(self):
        """
        Create a first superuser for dimail-api container. User creation is usually
        protected behind admin rights but dimail allows to create a first user
        when database is empty
        """
        response = requests.post(
            url=f"{DIMAIL_URL}/users/",
            headers={
                "accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": "Basic Og==",
            },
            json={
                "name": ADMIN_USERNAME,
                "password": ADMIN_PASSWORD,
                "is_admin": True,
            },
            timeout=10,
        )
        if response.status_code == status.HTTP_201_CREATED:
            self.stdout.write(
                self.style.SUCCESS(
                    "Succesfully created local dimail container's first admin !"
                )
            )

        if response.status_code == status.HTTP_403_FORBIDDEN:
            self.stdout.write(
                self.style.ERROR(
                    "Could not create first admin user, db already populated."
                )
            )
            return 1

    def encode64_for_basicauth(self, username, password):
        auth_string = f"{username}:{password}"
        return base64.b64encode(auth_string.encode("utf-8"))

    def create_regie_user(self):
        """
        Create local regie user
        """

        response = requests.post(
            url=f"{DIMAIL_URL}/users/",
            headers={
                "accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Basic {self.encode64_for_basicauth(ADMIN_USERNAME, ADMIN_PASSWORD)}",
            },
            json={
                "name": REGIE_USERNAME,
                "password": REGIE_USERNAME,
                "is_admin": False,
            },
            timeout=10,
        )

        if response.status_code != status.HTTP_201_CREATED:
            raise ("Régie user creation failed")
