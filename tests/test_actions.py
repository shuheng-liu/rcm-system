import string
import random
import pytest
from passlib.hash import pbkdf2_sha256
from mongoengine import connect
from mongoengine import ValidationError, NotUniqueError
from err import ActionError

# connect and initialize database
db = connect('rcm-test-db')


def clean_up(db=db):
    db.drop_database('rcm-test-db')


clean_up()


def random_user_info(length=5):
    rstr = lambda n: ''.join(random.choice(string.ascii_letters) for _ in range(n))
    email = rstr(length) + "@" + rstr(length) + ".com"
    password = rstr(length * 4)
    first_name = rstr(length * 2)
    last_name = rstr(length * 2)
    gender = random.choice("FM")
    return email, password, first_name, last_name, gender


def test_signup():
    from actions import signup
    from models import Student, Instructor, Staff

    for role in [Student, Instructor, Staff]:
        signup(role=role, email='john@doe.com', password='pwd', first_name='John', last_name='Doe', gender='M')
        john = role.objects(email='john@doe.com').first()
        assert john.first_name == 'John'
        assert john.last_name == 'Doe'
        assert john.email == 'john@doe.com'
        assert john.gender == 'M'
        assert pbkdf2_sha256.verify('pwd', john.password)

    # existing email
    for role in [Student, Instructor, Staff]:
        with pytest.raises(ActionError):
            signup(role=role, email='john@doe.com', password='pwd2', first_name='John2', last_name='Doe2', gender='M')

    # first_name / last_name too long
    for role in [Student, Instructor, Staff]:
        with pytest.raises(ValidationError):
            signup(role=role, email='jane@doe.com', password='pwd', first_name='a' * 101, last_name='Doe', gender='F')
        with pytest.raises(ValidationError):
            signup(role=role, email='jane@doe.com', password='pwd', first_name='Jane', last_name='a' * 101, gender='F')
        assert role.objects(email='jane@doe.com').count() == 0

    # student without gender
    with pytest.raises(ValidationError):
        signup(role=Student, email='jane@doe.com', password='pwd', first_name='Jane', last_name='Doe')

    clean_up()


def test_signin():
    from actions import signup
    from actions import signin
    from models import Student, Instructor, Staff

    for role in [Student, Instructor, Staff]:
        eml, pwd, fn, ln, gnd = random_user_info(length=5)
        signup(role=role, email=eml, password=pwd, first_name=fn, last_name=ln, gender=gnd)
        user = signin(role=role, email=eml, pwd_submitted=pwd)
        assert user.first_name == fn
        assert user.last_name == ln
        assert user.email == eml
        assert user.gender == gnd

        eml2, pwd2, _, _, _ = random_user_info(length=6)
        # Non-existent email
        with pytest.raises(ActionError):
            signin(role=role, email=eml2, pwd_submitted=pwd)
        # Incorrect password
        with pytest.raises(ActionError):
            signin(role=role, email=eml, pwd_submitted=pwd2)

    clean_up()


def test_change_password():
    from actions import signup, signin
    from actions import change_password
    from models import Student, Instructor, Staff

    for role in [Student, Instructor, Staff]:
        eml, pwd, fn, ln, gnd = random_user_info(length=5)
        _, pwd2, _, _, _ = random_user_info(length=6)
        user = signup(role=role, email=eml, password=pwd, first_name=fn, last_name=ln, gender=gnd)
        # Incorrect password, reject password changing
        with pytest.raises(ActionError):
            change_password(user, pwd2, pwd2)
        # Correct password; password changes to pwd2
        change_password(user, pwd, pwd2)
        # Sign in using new password
        signin(role=role, email=eml, pwd_submitted=pwd2)
        # Sign in using old password
        with pytest.raises(ActionError):
            signin(role, email=eml, pwd_submitted=pwd)

    clean_up()



