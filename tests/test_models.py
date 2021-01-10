from mongoengine import connect
from mongoengine import NotUniqueError
from mongoengine import ValidationError
import pytest

# connect and initialize database
db = connect('rcm-test-db')
db.drop_database('rcm-test-db')


def test_generic_user():
    from models import GenericUser
    GenericUser(first_name='John', last_name='Doe', email='john@doe.com', password='pwd').save()
    GenericUser(first_name='Jane', last_name='Doe', email='jane@doe.com', password='pwd', gender='F').save()
    GenericUser(first_name='James', last_name='Bond', email='james@bond.com', password='pwd', gender='M').save()

    # duplicate email
    with pytest.raises(NotUniqueError):
        GenericUser(first_name='John2', last_name='Doe2', email='john@doe.com', password='pwd2').save()
    # illegal gender
    with pytest.raises(ValidationError):
        GenericUser(first_name="Jane2", last_name="Doe2", email='jane2@doe2.com', password='pwd', gender='N').save()
    # first name too long
    with pytest.raises(ValidationError):
        GenericUser(first_name="A" * 101, last_name="Doe2", email='jane2@doe2.com', password='pwd', gender='M').save()
    # required fields missing
    with pytest.raises(ValidationError):
        GenericUser(first_name='Johnny').save()


def test_student():
    from models import Student
    Student(first_name='John', last_name='Doe', email='john@doe.com', password='pwd', gender='M').save()
    Student(first_name='James', last_name='Bond', email='james@bond.com', password='pwd', gender='M', aka='007').save()
    Student(first_name='Jane', last_name='Doe', email='jane@doe.com', password='pwd', gender='F',
            req_for_courses=[]).save()

    # TODO add a nonempty `req_for_courses` test case

    assert Student.objects(req_for_courses__size=0).count() == 3

    # missing gender
    with pytest.raises(ValidationError):
        Student(first_name='John2', last_name='Doe2', email='john@doe.com', password='pwd').save()
