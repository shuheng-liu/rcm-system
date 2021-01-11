import string
import random
import pytest
from datetime import date, datetime
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


def reload(*documents):
    for doc in documents:
        doc.reload()


def signup_random_user(role, length=5):
    from actions import signup
    eml, pwd, fn, ln, gnd = random_user_info(length=length)
    return signup(role, email=eml, password=pwd, first_name=fn, last_name=ln, gender=gnd)


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


def test_new_course():
    from actions import signup, signin
    from actions import new_course
    from models import Instructor
    prof = signup_random_user(Instructor, length=5)
    cs101 = new_course(code='CS101', start_date=date.today(), course_name='Intro to CS', professor=prof)
    prof.reload()
    assert cs101 in prof.courses
    assert cs101.professor == prof
    # duplicate course name is fine
    cs102 = new_course(code='CS102', start_date=date.today(), course_name='Intro to CS', professor=prof)
    prof.reload()
    assert cs102 in prof.courses
    assert cs102.professor == prof

    # duplicate course code results in error
    with pytest.raises(NotUniqueError):
        new_course(code='CS101', start_date=date.today(), course_name='Intro to CS2', professor=prof)
    # course code too long
    with pytest.raises(ValidationError):
        new_course(code='C' * 16, start_date=date.today(), course_name='Intro to CS2', professor=prof)
    # course name too long
    with pytest.raises(ValidationError):
        new_course(code='CS103', start_date=date.today(), course_name='a' * 1001, professor=prof)

    clean_up()


def test_set_letter_quota():
    from actions import signup, signin, new_course
    from actions import set_letter_quota
    from models import Student, Instructor, Course

    std = signup_random_user(Student, length=5)
    prof1 = signup_random_user(Instructor, length=6)
    prof2 = signup_random_user(Instructor, length=7)
    cs101 = new_course(code='CS101', start_date=date.today(), course_name='Intro to CS', professor=prof1)
    pl102 = new_course(code='PL102', start_date=date.today(), course_name='Politics', professor=prof2)

    # set quota for (cs101, prof1) for the first time
    set_letter_quota(student=std, recommender=prof1, course=cs101, quota=10)
    std_db = Student.objects.first()
    course = Course.objects(code='CS101').first()
    assert std_db.req_for_courses.count() == 1
    assert std_db.req_for_courses.first().recommender == prof1
    assert std_db.req_for_courses.first().course == cs101
    assert std_db.req_for_courses.first().requests_quota == 10
    assert len(course.students) == 1

    # force reset quota for (cs101, prof1)
    set_letter_quota(student=std, recommender=prof1, course=cs101, quota=20, reset=True)
    std_db = Student.objects.first()
    assert std_db.req_for_courses.count() == 1
    assert std_db.req_for_courses.first().recommender == prof1
    assert std_db.req_for_courses.first().course == cs101
    assert std_db.req_for_courses.first().requests_quota == 20

    # reset quota for (cs101, prof1) without explicit allowing reset, even under the same quota
    with pytest.raises(ActionError):
        set_letter_quota(student=std, recommender=prof1, course=cs101, quota=20)

    # negative quota (reset)
    with pytest.raises(ValidationError):
        set_letter_quota(student=std, recommender=prof1, course=cs101, quota=-10, reset=True)
    # negative quota (set for the first time)
    with pytest.raises(ValidationError):
        set_letter_quota(student=std, recommender=prof2, course=pl102, quota=-20)

    # set quota for (cs101, prof2), req_for_courses.count() changes to 2
    set_letter_quota(student=std, recommender=prof2, course=cs101, quota=30)
    # set quota for (pl102, prof1), req_for_courses.count() changes to 3
    set_letter_quota(student=std, recommender=prof1, course=pl102, quota=40)
    # set quota for (pl102, prof2), req_for_courses.count() changes to 4
    set_letter_quota(student=std, recommender=prof2, course=pl102, quota=50)

    std_db = Student.objects.first()
    assert std_db.req_for_courses.count() == 4

    for course in Course.objects:
        assert len(course.students) == 1

    clean_up()


def test_reset_course_professor():
    from actions import signup, new_course
    from actions import reset_course_professor
    from models import Instructor, Course
    prof1 = signup_random_user(Instructor, length=5)
    prof2 = signup_random_user(Instructor, length=6)

    # create a new course and set professor
    course = new_course(code='CS101', start_date=date.today(), course_name='Intro to CS', professor=prof1)
    reload(prof1, prof2, course)
    assert course.professor == prof1
    assert course in prof1.courses
    assert course not in prof2.courses

    # reset to the same professor
    reset_course_professor(course=course, professor=prof1)
    reload(prof1, prof2, course)
    assert course.professor == prof1
    assert course in prof1.courses
    assert course not in prof2.courses

    # reset to another professor, after revoking original access
    reset_course_professor(course=course, professor=prof2)
    reload(prof1, prof2, course)
    assert course.professor == prof2
    assert course not in prof1.courses
    assert course in prof2.courses

    # reset to another professor, w/o revoking original access
    reset_course_professor(course=course, professor=prof1, revoke_access=False)
    reload(prof1, prof2, course)
    assert course.professor == prof1
    assert course in prof1.courses
    assert course in prof2.courses


def test_set_course_coordinator():
    from actions import signup, new_course
    from actions import set_course_coordinator
    from models import Instructor, Course, Staff
    prof = signup_random_user(Instructor, length=5)
    coordinator1 = signup_random_user(Staff, length=5)
    coordinator2 = signup_random_user(Staff, length=6)

    # create a new course and set coordinator
    course = new_course(code='CS101', start_date=date.today(), course_name='Intro to CS', professor=prof)
    set_course_coordinator(course, coordinator1)
    reload(course, coordinator1, coordinator2)
    assert course.coordinator == coordinator1
    assert course in coordinator1.accessible_courses
    assert course not in coordinator2.accessible_courses

    # reset to another coordinator, revoking access from previous coordinator
    set_course_coordinator(course, coordinator2)
    reload(course, coordinator1, coordinator2)
    assert course not in coordinator1.accessible_courses
    assert course in coordinator2.accessible_courses

    # reset to another coordinator, w/o revoking access from previous coordinator
    set_course_coordinator(course, coordinator1, revoke_access=False)
    reload(course, coordinator1, coordinator2)
    assert course in coordinator1.accessible_courses
    assert course in coordinator2.accessible_courses

    clean_up()


def test_assign_course_mentor():
    from actions import new_course
    from actions import assign_course_mentor
    from models import Instructor
    prof = signup_random_user(Instructor, length=5)
    mentor1 = signup_random_user(Instructor, length=6)
    mentor2 = signup_random_user(Instructor, length=7)

    course = new_course(code='CS101', start_date=date.today(), course_name='Intro to CS', professor=prof)
    assign_course_mentor(course, mentor1)
    assign_course_mentor(course, mentor1)
    assign_course_mentor(course, mentor2)
    reload(course, mentor1, mentor2)

    assert len(course.mentors) == 2
    assert mentor1 in course.mentors
    assert mentor2 in course.mentors
    assert course in mentor1.courses
    assert course in mentor2.courses

    clean_up()


def test_withdraw_course_mentor():
    from actions import new_course
    from actions import withdraw_course_mentor
    from models import Instructor

    prof = signup_random_user(Instructor, length=5)
    mentor1 = signup_random_user(Instructor, length=6)

    course = new_course(code='CS101', start_date=date.today(), course_name='Intro to CS', professor=prof)
    assign_course_mentor(course, mentor1)
    withdraw_course_mentor(course, mentor1)
    update(course, mentor1)
    assert mentor1 not in course.mentors
    assert course not in mentor1.courses

    # withdraw the same mentor twice
    mentor2 = signup_random_user(Instructor, length=7)
    assign_course_mentor(course, mentor1)
    assign_course_mentor(course, mentor2)
    # w/o revoking access
    withdraw_course_mentor(course, mentor2, revoke_access=False)
    update(course, mentor1, mentor2)
    assert mentor1 in course.mentors
    assert mentor2 not in course.mentors
    assert course in mentor1.courses
    assert course in mentor2.courses
    # revoking access
    withdraw_course_mentor(course, mentor2, revoke_access=True)
    update(course, mentor1, mentor2)
    assert mentor1 in course.mentors
    assert mentor2 not in course.mentors
    assert course in mentor1.courses
    assert course not in mentor2.courses
