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
