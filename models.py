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
from mongoengine import BooleanField
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
    requests_sent = ListField(ReferenceField('Request'))
    requests_quota = IntField(min_value=0, required=True)


class Student(User):
    gender = StringField(regex='(M|F)', max_length=1, min_length=1, required=True)
    aka = StringField(max_length=20)
    req_for_courses = EmbeddedDocumentListField(RequestForCourse)


class Instructor(User):
    courses = ListField(ReferenceField('Course'))
    requests_received = ListField(ReferenceField('Request'))


class Staff(User):
    full_access = BooleanField(default=False, required=True)
    accessible_courses = ListField(ReferenceField('Course'))


class Course(Document):
    code = StringField(max_length=15, required=True, unique=True)
    course_name = StringField(max_length=1000)
    start_date = DateField(default=datetime.today, required=True)
    professor = ReferenceField(Instructor, required=True)
    mentors = ListField(ReferenceField(Instructor))
    coordinator = ReferenceField(Staff)
    students = ListField(ReferenceField(Student))


class Message(EmbeddedDocument):
    from_user = ReferenceField(User, required=True)
    content = StringField(max_length=500, required=True)
    timestamp = DateTimeField(default=datetime.utcnow, required=True)


STATUS_REQUESTED = 1000
STATUS_EMAILED = 2000
STATUS_DRAFTED = 3000
STATUS_FULFILLED = 4000


def _validate_request_status(status):
    if status not in [
        STATUS_REQUESTED,
        STATUS_EMAILED,
        STATUS_DRAFTED,
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
    date_fulfilled = DateField()
    status = IntField(validation=_validate_request_status, default=STATUS_REQUESTED, required=True)
    messages = EmbeddedDocumentListField(Message)

    def clean(self):
        if (self.date_fulfilled is None) and (self.status == STATUS_FULFILLED):
            raise ValidationError('Request fulfilled but not specified when')
        if (self.date_fulfilled is not None) and (self.status != STATUS_FULFILLED):
            raise ValidationError('Request not fulfilled but date_fulfilled is set')
