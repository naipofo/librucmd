"""A small cmd utility to access school data"""
from os.path import isfile
import json
from pathlib import Path
from typing import Optional
import requests
from pydantic import BaseModel, Field, validator


class AuthData(BaseModel):
    """Authentication data"""

    access_token: str
    refresh_token: str


def get_auth() -> AuthData:
    """Load auth data for service"""
    data = None
    if isfile("_token.json"):
        data = Path("_token.json").read_text(encoding="utf8")
    else:
        data = requests.post(
            "https://api.librus.pl/OAuth/TokenJST",
            timeout=1000,
            data={
                "grant_type": "implicit_grant",
                "client_id": 59,
                "secret": input("Enter secret: "),
                "code": input("Enter code: "),
                "pin": input("Enter pin: "),
                "librus_rules_accepted": "true",
                "librus_mobile_rules_accepted": "true",
                "librus_long_term_token": 1,
            },
        ).text
        print(data)
        with open("_token.json", "w", encoding="utf8") as file:
            file.write(data)
    return AuthData(**json.loads(data))


class Account(BaseModel):
    """Basic account data"""

    first_name: str = Field(alias="FirstName")
    last_name: str = Field(alias="LastName")
    email: str = Field(alias="Email")

    @property
    def full_name(self) -> str:
        """full name"""
        return f"{self.first_name} {self.last_name}"


def extract_id(value: dict) -> any:
    """Extract id from dict"""
    return value["Id"]


class Grade(BaseModel):
    """A single grade"""

    grade: str = Field(alias="Grade")
    added_by: int = Field(alias="AddedBy")
    category: int = Field(alias="Category")
    subject: int = Field(alias="Subject")
    comment: Optional[int] = Field(alias="Comments")

    _validate = validator("added_by", "category", "subject", pre=True)(extract_id)
    _validate2 = validator("comment", pre=True)(lambda cls, v: extract_id(v[0]))


class User(BaseModel):
    """A single user"""

    first_name: str = Field(alias="FirstName")
    last_name: str = Field(alias="LastName")


class Subject(BaseModel):
    """A single subject"""

    name: str = Field(alias="Name")
    short: str = Field(alias="Short")


class Category(BaseModel):
    """A single category"""

    name: str = Field(alias="Name")
    weight: Optional[int] = Field(alias="Weight")


class Comment(BaseModel):
    """A single comment"""

    text: str = Field(alias="Text")


class LibruApp:
    """Main service interface"""

    grades: dict[int, Grade] = dict()
    users: dict[int, User] = dict()
    subjects: dict[int, Subject] = dict()
    categories: dict[int, Category] = dict()
    comments: dict[int, Comment] = dict()
    account: Account
    auth: AuthData

    def __init__(self, auth: AuthData) -> None:
        self.auth = auth

    def call(self, endpoint: str) -> str:
        """Generic api call"""
        return requests.get(
            f"https://api.librus.pl/3.0/{endpoint}",
            headers={"Authorization": f"Bearer {self.auth.access_token}"},
            timeout=1000,
        ).text

    def load_set(self, name: str, obj_type: type, endpoint: Optional[str] = None):
        """load a set of data"""
        for item in json.loads(self.call(name if endpoint is None else endpoint))[name]:
            getattr(self, name.lower())[item["Id"]] = obj_type(**item)

    def load(self):
        """Load data from service"""
        self.account = Account(**json.loads(self.call("Me"))["Me"]["Account"])
        self.load_set("Grades", Grade)
        self.load_set("Users", User)
        self.load_set("Subjects", Subject)
        self.load_set("Categories", Category, "Grades/Categories")
        self.load_set("Comments", Comment, "Grades/Comments")


def main():
    """main"""
    app = LibruApp(auth=get_auth())
    app.load()

    print(f"Witaj {app.account.full_name}, twój email to {app.account.email}")
    print("Dostępne przedmioty: ")
    for key, val in app.subjects.items():
        print(f"{key} - {val.name}")
    subject = int(input("Jaki przedmiot wyświetlić? "))
    for _, val in app.grades.items():
        if val.subject == subject:
            print(
                f"Ocena {val.grade}: " + app.comments[val.comment].text
                if val.comment is not None
                else "bez komentarza"
            )


if __name__ == "__main__":
    main()
