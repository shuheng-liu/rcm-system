import pytest
from datetime import date, datetime
from mongoengine import connect
from mongoengine import NotUniqueError
from mongoengine import ValidationError

# connect and initialize database
db = connect('rcm-test-db')
db.drop_database('rcm-test-db')


def clean_up(db=db):
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

    clean_up()


def test_student():
    from models import Student
    Student(first_name='John', last_name='Doe', email='john@doe.com', password='pwd', gender='M').save()
    Student(first_name='James', last_name='Bond', email='james@bond.com', password='pwd', gender='M', aka='007').save()
    Student(first_name='Jane', last_name='Doe', email='jane@doe.com', password='pwd', gender='F',
            req_for_courses=[]).save()

    # TODO add a nonempty `req_for_courses` test case
    pass

    assert Student.objects(req_for_courses__size=0).count() == 3

    # missing gender
    with pytest.raises(ValidationError):
        Student(first_name='John2', last_name='Doe2', email='john@doe.com', password='pwd').save()

    clean_up()


def test_instructor():
    from models import Instructor
    Instructor(first_name='Joe', last_name='Biden', email='joe@biden.com', password='pwd', gender='M',
               courses=[]).save()
    Instructor(first_name='Kamala', last_name='Harris', email='kamala@harris.com', password='pwd', gender='F',
               requests_received=[]).save()
    Instructor(first_name='Nancy', last_name='Pelosi', email='nancy@pelosi.com', password='pwd').save()
    # TODO add a nonempty `request_received` test case
    pass

    # TODO add a nonempty `courses` test case
    pass

    clean_up()


def test_staff():
    from models import Staff

    Staff(first_name='Tony', last_name='Stark', email='tony@stark.com', password='pwd', gender='M',
          full_access=True).save()
    Staff(first_name='Pepper', last_name='Potts', email='pepper@potts.com', password='pwd', gender='F').save()
    Staff(first_name='Morgan', last_name='Stark', email='morgan@stark.com', password='pwd', gender='F',
          accessible_courses=[]).save()

    # TODO add a nonempty `accessible_couress` test case
    pass

    clean_up()


def test_course():
    from models import Course, Instructor, Staff, Student
    today = date.today()

    # instructors
    joe = Instructor(first_name='Joe', last_name='Biden', email='joe@biden.com', password='pwd').save()
    tony = Instructor(first_name='Tony', last_name='Stark', email='tony@stark.com', password='pwd').save()
    kamala = Instructor(first_name='Kamala', last_name='Harris', email='kamala@harris.com', password='pwd').save()
    pepper = Instructor(first_name='Pepper', last_name='Potts', email='pepper@potts.com', password='pwd').save()
    morgan = Instructor(first_name='Morgan', last_name='Stark', email='morgan@stark.com', password='pwd').save()

    # coordinators
    james = Staff(first_name='James', last_name='Bond', email='james@bond.com', password='pwd').save()
    eve = Staff(first_name='Eve', last_name='Moneypenny', email='eve@moneypenny.com', password='pwd').save()

    # students
    john = Student(first_name='John', last_name='Doe', email='john@doe.com', password='pwd', gender='M').save()
    jane = Student(first_name='Jane', last_name='Doe', email='jane@doe.com', password='pwd', gender='F').save()

    # w/o start_date
    Course(code='PL999', course_name='US Presidency', professor=joe).save()
    # w/ start_date
    Course(code='PL888', start_date=today, course_name='US Senatorship', professor=joe).save()
    # w/o mentors, coordinator, and students
    Course(code='PL101', course_name='Introduction to Politics', professor=joe).save()
    # w/ single mentor; w/o coordinator and students
    Course(code='PL102', course_name='Intermediate Politics', professor=joe, mentors=[kamala]).save()
    # w/ mentors and coordinator; w/o students
    Course(code='CS101', course_name='Introduction to Computer Science',
           professor=tony, mentors=[pepper, morgan], coordinator=james).save()
    # w/ mentors, coordinator, and students
    Course(code='CS103', course_name='Advanced Computer Science',
           professor=tony, mentors=[pepper, morgan], coordinator=eve, students=[john, jane]).save()

    # w/o professor
    with pytest.raises(ValidationError):
        Course(code='PL103', course_name='Advanced Politics').save()
    # duplicate course code
    with pytest.raises(NotUniqueError):
        Course(code='CS103', course_name='Computational Science', professor=tony).save()

    clean_up()


def test_request():
    from models import Student, Instructor, Course
    from models import Request
    from models import STATUS_REQUESTED, STATUS_EMAILED, STATUS_UNFULFILLED, STATUS_FULFILLED

    ILLEGAL_STATUS = 1234

    # date
    today = date.today()
    # instructor & student
    joe = Instructor(first_name='Joe', last_name='Biden', email='joe@biden.com', password='pwd').save()
    john = Student(first_name='John', last_name='Doe', email='john@doe.com', password='pwd', gender='M').save()
    # course
    pl999 = Course(code='PL999', course_name='US Presidency', professor=joe).save()

    # w/ everything filled (except for messages)
    Request(student=john, instructor=joe, course=pl999,
            school_applied='Harvard', program_applied='Politics', deadline=today,
            date_created=today, date_updated=today, date_fulfilled=today, status=STATUS_FULFILLED).save()
    # w/o date_created
    Request(student=john, instructor=joe, course=pl999,
            school_applied='Harvard', program_applied='Politics', deadline=today,
            date_updated=today, date_fulfilled=today, status=STATUS_FULFILLED).save()
    # w/o date_fulfilled
    Request(student=john, instructor=joe, course=pl999,
            school_applied='Harvard', program_applied='Politics', deadline=today,
            date_created=today, date_updated=today, status=STATUS_UNFULFILLED).save()

    # w/o student
    with pytest.raises(ValidationError):
        Request(instructor=joe, course=pl999,
                school_applied='Harvard', program_applied='Politics', deadline=today,
                date_created=today, date_updated=today, date_fulfilled=today, status=STATUS_FULFILLED).save()
    # w/o professor
    with pytest.raises(ValidationError):
        Request(student=john, course=pl999,
                school_applied='Harvard', program_applied='Politics', deadline=today,
                date_created=today, date_updated=today, date_fulfilled=today, status=STATUS_FULFILLED).save()
    # w/o course
    with pytest.raises(ValidationError):
        Request(student=john, instructor=joe,
                school_applied='Harvard', program_applied='Politics', deadline=today,
                date_created=today, date_updated=today, date_fulfilled=today, status=STATUS_FULFILLED).save()
    # w/o school_applied
    with pytest.raises(ValidationError):
        Request(student=john, instructor=joe, course=pl999,
                program_applied='Politics', deadline=today,
                date_created=today, date_updated=today, date_fulfilled=today, status=STATUS_FULFILLED).save()
    # w/o program_applied
    with pytest.raises(ValidationError):
        Request(student=john, instructor=joe, course=pl999,
                school_applied='Harvard', deadline=today,
                date_created=today, date_updated=today, date_fulfilled=today, status=STATUS_FULFILLED).save()
    # w/o deadline
    with pytest.raises(ValidationError):
        Request(student=john, instructor=joe, course=pl999,
                school_applied='Harvard', program_applied='Politics',
                date_created=today, date_updated=today, date_fulfilled=today, status=STATUS_FULFILLED).save()
    # w/o date_fulfilled but status==STATUS_FULFILLED
    with pytest.raises(ValidationError):
        Request(student=john, instructor=joe, course=pl999,
                school_applied='Harvard', program_applied='Politics', deadline=today,
                date_created=today, date_updated=today, status=STATUS_FULFILLED).save()
    # w/ date_fulfilled but status!=STATUS_FULFILLED
    with pytest.raises(ValidationError):
        Request(student=john, instructor=joe, course=pl999,
                school_applied='Harvard', program_applied='Politics', deadline=today,
                date_created=today, date_updated=today, date_fulfilled=today, status=STATUS_REQUESTED).save()
    # illegal status
    with pytest.raises(ValidationError):
        Request(student=john, instructor=joe, course=pl999,
                school_applied='Harvard', program_applied='Politics', deadline=today,
                date_created=today, date_updated=today, date_fulfilled=today, status=ILLEGAL_STATUS).save()
    # School name too long
    with pytest.raises(ValidationError):
        Request(student=john, instructor=joe, course=pl999,
                school_applied='Harvard' * 10, program_applied='Politics', deadline=today,
                date_created=today, date_updated=today, date_fulfilled=today, status=STATUS_FULFILLED).save()
    # Program name too long
    with pytest.raises(ValidationError):
        Request(student=john, instructor=joe, course=pl999,
                school_applied='Harvard', program_applied='Politics' * 10, deadline=today,
                date_created=today, date_updated=today, date_fulfilled=today, status=STATUS_FULFILLED).save()

    # TODO add test case for nonempty `messages`

    clean_up()


def test_message():
    from models import Message
    from models import Student, Instructor

    # datetime
    now = datetime.utcnow
    # instructor & student
    joe = Instructor(first_name='Joe', last_name='Biden', email='joe@biden.com', password='pwd').save()
    john = Student(first_name='John', last_name='Doe', email='john@doe.com', password='pwd', gender='M').save()

    # from student
    msg = Message(sender=john, content="Hello, Joe!", time=now())
    msg.validate()
    assert msg.sender == 'John Doe'
    # from instructor
    msg = Message(sender=joe, content="Hello, John!", time=now())
    msg.validate()
    assert msg.sender == 'Joe Biden'
    # custom sender_name
    msg = Message(sender='US President', content="Hello, John!", time=now())
    msg.validate()
    assert msg.sender == 'US President'
    # w/o time
    Message(sender=john, content="Hello, again!").validate()

    # content too long
    with pytest.raises(ValidationError):
        Message(sender=joe, content="a" * 501).validate()

    clean_up()


def test_request_for_course():
    from models import RequestForCourse
    from models import Course, Instructor, Staff, Student
    from models import Instructor

    joe = Instructor(first_name='Joe', last_name='Biden', email='joe@biden.com', password='pwd').save()
    pl999 = Course(code='PL999', course_name='US Presidency', professor=joe).save()

    RequestForCourse(course=pl999, requests_quota=8, recommender=joe).validate()

    # negative quota
    with pytest.raises(ValidationError):
        RequestForCourse(course=pl999, requests_quota=-1, recommender=joe).validate()
    # missing quota
    with pytest.raises(ValidationError):
        RequestForCourse(course=pl999, recommender=joe).validate()
    # missing recommender
    with pytest.raises(ValidationError):
        RequestForCourse(course=pl999, requests_quota=10).validate()
    # missing course
    with pytest.raises(ValidationError):
        RequestForCourse(requests_quota=10, recommender=joe).validate()

    clean_up()


def test_deletion_rules():
    # TODO test reverse delete rules
    pass
