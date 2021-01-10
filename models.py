from datetime import datetime

import mongoengine
from mongoengine import Document
from mongoengine import EmbeddedDocument
from mongoengine import StringField
from mongoengine import EmailField
from mongoengine import ComplexDateTimeField
from mongoengine import DateTimeField
from mongoengine import DateField
from mongoengine import ListField
from mongoengine import ReferenceField
from mongoengine import LazyReferenceField
from mongoengine import EmbeddedDocumentField
from mongoengine import EmbeddedDocumentListField
from mongoengine import IntField
from mongoengine import StringField
from mongoengine import ValidationError


class User(Document):
    email = EmailField(unique=True, required=True)
    password = StringField(max_length=100, required=True)
    first_name = StringField(max_length=100, required=True)
    last_name = StringField(max_length=100, required=True)
    gender = StringField(regex='(M|F)', max_length=1, min_length=1)

    meta = {"abstract": True}


class GenericUser(User):
    pass


class RequestForCourse(EmbeddedDocument):
    course = ReferenceField('Course', required=True)
    requests_sent = ListField(ReferenceField('Request'), default=list, required=True)
    requests_quota = IntField(min_value=0, required=True)


class Student(User):
    gender = StringField(regex='(M|F)', max_length=1, min_length=1, required=True)
    aka = StringField(max_length=20)
    courses = EmbeddedDocumentListField(RequestForCourse, default=list, required=True)


class Instructor(User):
    courses = ListField(ReferenceField('Course'), default=list, required=True)
    requests_received = ListField(ReferenceField('Request'), default=list, required=True)


class Staff(User):
    pass


class Course(Document):
    code = StringField(max_length=15, required=True, unique=True)
    course_name = StringField(max_length=1000)
    start_date = DateField(default=datetime.today, required=True)
    professor = ReferenceField(Instructor, required=True)
    mentors = ListField(ReferenceField(Instructor), required=True, default=list)
    coordinator = ReferenceField(Staff)
    students = ListField(ReferenceField(Student), required=True, default=list)


class Message(EmbeddedDocument):
    from_user = ReferenceField(User, required=True)
    content = StringField(max_length=500, required=True)
    timestamp = DateTimeField(default=datetime.utcnow, required=True)


STATUS_REQUESTED = 100
STATUS_EMAILED = 200
STATUS_FULFILLED = 300


def _validate_request_status(status):
    if status not in [
        STATUS_REQUESTED,
        STATUS_EMAILED,
        STATUS_FULFILLED,
    ]:
        raise ValidationError(f'Illegal Status: {status}')


class Request(Document):
    student = ReferenceField(Student, required=True)
    instructor = ReferenceField(Instructor, required=True)
    course = ReferenceField(Course, required=True)
    school_applied = StringField(max_length=50, required=True)
    program_applied = StringField(max_length=50, required=True)
    deadline = DateField(required=True)
    date_created = DateField(default=datetime.utcnow, required=True)
    date_updated = DateField(default=datetime.utcnow, required=True)
    date_responded = DateField()
    status = StringField(validation=_validate_request_status, required=True)
    messages = EmbeddedDocumentListField(Message)
