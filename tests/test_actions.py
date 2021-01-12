import string
import random
import pytest
from datetime import date, datetime, timedelta
from passlib.hash import pbkdf2_sha256
from mongoengine import connect
from mongoengine import ValidationError, NotUniqueError, DoesNotExist
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
    from actions import new_course, assign_course_mentor
    from actions import withdraw_course_mentor
    from models import Instructor

    prof = signup_random_user(Instructor, length=5)
    mentor1 = signup_random_user(Instructor, length=6)

    course = new_course(code='CS101', start_date=date.today(), course_name='Intro to CS', professor=prof)
    assign_course_mentor(course, mentor1)
    withdraw_course_mentor(course, mentor1)
    reload(course, mentor1)
    assert mentor1 not in course.mentors
    assert course not in mentor1.courses

    # withdraw the same mentor twice
    mentor2 = signup_random_user(Instructor, length=7)
    assign_course_mentor(course, mentor1)
    assign_course_mentor(course, mentor2)
    # w/o revoking access
    withdraw_course_mentor(course, mentor2, revoke_access=False)
    reload(course, mentor1, mentor2)
    assert mentor1 in course.mentors
    assert mentor2 not in course.mentors
    assert course in mentor1.courses
    assert course in mentor2.courses
    # revoking access
    withdraw_course_mentor(course, mentor2, revoke_access=True)
    reload(course, mentor1, mentor2)
    assert mentor1 in course.mentors
    assert mentor2 not in course.mentors
    assert course in mentor1.courses
    assert course not in mentor2.courses

    clean_up()


def test_grant_access():
    from actions import new_course
    from actions import grant_access
    from models import Instructor, Staff

    prof = signup_random_user(Instructor, length=5)
    staff = signup_random_user(Staff, length=5)

    cs101 = new_course(code='CS101', start_date=date.today(), course_name='Intro to CS', professor=prof)
    grant_access(staff=staff, course=cs101)
    reload(staff, cs101)
    assert cs101 in staff.accessible_courses

    pl102 = new_course(code='PL102', start_date=date.today(), course_name='Politics', professor=prof)
    grant_access(staff=staff, course=pl102)
    reload(staff, cs101, pl102)
    assert pl102 in staff.accessible_courses

    # grant the first course again, there shouldn't be duplicate
    grant_access(staff=staff, course=cs101)
    reload(staff, cs101, pl102)
    assert len(staff.accessible_courses) == 2

    clean_up()


def test_revoke_access():
    from actions import new_course, grant_access
    from actions import revoke_access
    from models import Instructor, Staff

    prof = signup_random_user(Instructor, length=5)
    staff = signup_random_user(Staff, length=5)
    cs101 = new_course(code='CS101', start_date=date.today(), course_name='Intro to CS', professor=prof)
    pl102 = new_course(code='PL102', start_date=date.today(), course_name='Politics', professor=prof)
    grant_access(staff=staff, course=cs101)
    grant_access(staff=staff, course=cs101)
    grant_access(staff=staff, course=pl102)

    revoke_access(staff=staff, course=cs101)
    reload(staff, cs101, pl102)
    assert cs101 not in staff.accessible_courses
    assert pl102 in staff.accessible_courses
    revoke_access(staff=staff, course=pl102)
    reload(staff, cs101, pl102)
    assert cs101 not in staff.accessible_courses
    assert pl102 not in staff.accessible_courses

    clean_up()


def test_make_request():
    from actions import signup, new_course, set_letter_quota
    from actions import make_request
    from models import Instructor, Student
    prof = signup_random_user(Instructor, length=5)
    std = signup_random_user(Student, length=5)
    today = date.today()
    cs101 = new_course(code='CS101', start_date=today, course_name='Intro to CS', professor=prof)
    pl102 = new_course(code='PL102', start_date=today, course_name='Politics', professor=prof)
    reload(prof)

    # assign 2 quota for (cs101, prof)
    set_letter_quota(student=std, recommender=prof, course=cs101, quota=2)
    # make a request, 1 quota remaining
    req = make_request(
        student=std,
        instructor=prof,
        course=cs101,
        school_applied='UC',
        program_applied='CS',
        deadline=today,
    )
    reload(std, prof, req)
    r4c = std.req_for_courses.filter(course=cs101).get()
    assert len(r4c.requests_sent) == 1
    assert r4c.requests_quota == 1
    assert req in r4c.requests_sent
    assert req in prof.requests_received
    assert req.student == std
    assert req.instructor == prof
    assert req.course == cs101
    assert req.school_applied == 'UC'
    assert req.program_applied == 'CS'
    assert req.deadline == today

    # make another request, 0 quota remaining
    req = make_request(
        student=std,
        instructor=prof,
        course=cs101,
        school_applied='UC2',
        program_applied='CS2',
        deadline=today,
    )
    reload(std, prof, req)
    r4c = std.req_for_courses.filter(course=cs101).get()
    assert len(r4c.requests_sent) == 2
    assert r4c.requests_quota == 0
    assert req in r4c.requests_sent
    assert req in prof.requests_received
    assert req.student == std
    assert req.instructor == prof
    assert req.course == cs101
    assert req.school_applied == 'UC2'
    assert req.program_applied == 'CS2'
    assert req.deadline == today

    # raises error because no quota remains
    with pytest.raises(DoesNotExist):
        make_request(
            student=std,
            instructor=prof,
            course=cs101,
            school_applied='UC2',
            program_applied='CS2',
            deadline=today,
        )

    # raises error because no quota assigned
    with pytest.raises(DoesNotExist):
        make_request(
            student=std,
            instructor=prof,
            course=pl102,
            school_applied='UC3',
            program_applied='CS3',
            deadline=today,
        )

    # assign 1 quota for (pl102, prof)
    set_letter_quota(student=std, recommender=prof, course=pl102, quota=1)
    req = make_request(
        student=std,
        instructor=prof,
        course=pl102,
        school_applied='Yale',
        program_applied='Politics',
        deadline=today,
    )
    reload(std, prof, req)
    r4c = std.req_for_courses.filter(course=pl102).get()
    assert len(r4c.requests_sent) == 1
    assert r4c.requests_quota == 0
    assert req in r4c.requests_sent
    assert req in prof.requests_received
    assert req.student == std
    assert req.instructor == prof
    assert req.course == pl102
    assert req.school_applied == 'Yale'
    assert req.program_applied == 'Politics'
    assert req.deadline == today

    clean_up()


def test_withdraw_request():
    from actions import signup, new_course, set_letter_quota, make_request
    from actions import withdraw_request
    from models import Instructor, Student, Request
    from models import STATUS_EMAILED, STATUS_REQUESTED, STATUS_DRAFTED, STATUS_FULFILLED
    prof = signup_random_user(Instructor, length=5)
    std = signup_random_user(Student, length=5)
    today = date.today()
    cs101 = new_course(code='CS101', start_date=today, course_name='Intro to CS', professor=prof)
    set_letter_quota(student=std, recommender=prof, course=cs101, quota=2)
    req = make_request(student=std, instructor=prof, course=cs101, school_applied='UC', program_applied='CS',
                       deadline=today)
    withdraw_request(student=std, request=req)
    reload(std, prof)
    assert Request.objects.count() == 0
    assert len(std.req_for_courses.get().requests_sent) == 0
    assert std.req_for_courses.get().requests_quota == 2
    assert len(prof.requests_received) == 0

    # withdraw a non-existent request
    with pytest.raises(DoesNotExist):
        withdraw_request(student=std, request=req)

    # withdraw a fulfilled request
    req_fulfilled = make_request(student=std, instructor=prof, course=cs101, school_applied='UC',
                                 program_applied='CS', deadline=today)
    req_fulfilled.date_fulfilled = today
    req_fulfilled.status = STATUS_FULFILLED
    req_fulfilled.save()
    reload(std, prof)
    assert len(std.req_for_courses.get().requests_sent) == 1
    assert std.req_for_courses.get().requests_quota == 1
    assert len(prof.requests_received) == 1
    with pytest.raises(ActionError):
        withdraw_request(student=std, request=req_fulfilled)

    # withdraw an unrelated request
    std2 = signup_random_user(Student, length=6)
    prof2 = signup_random_user(Instructor, length=6)
    pl102 = new_course(code='PL102', start_date=today, course_name='Politics', professor=prof2)
    set_letter_quota(student=std2, recommender=prof2, course=pl102, quota=2)
    req2 = make_request(student=std2, instructor=prof2, course=pl102, school_applied='UC2', program_applied='CS2',
                        deadline=today)
    with pytest.raises(DoesNotExist):
        withdraw_request(student=std, request=req2)
    reload(std, std2, prof, prof2)

    # removing a request not attached to the student shouldn't delete the request
    assert Request.objects.count() == 2
    assert len(std2.req_for_courses.get().requests_sent) == 1
    assert req2 in std2.req_for_courses.get().requests_sent
    assert std2.req_for_courses.get().requests_quota == 1
    assert len(prof2.requests_received) == 1

    # and it shouldn't affect other students/staffs
    assert len(std.req_for_courses.get().requests_sent) == 1
    assert std.req_for_courses.get().requests_quota == 1
    assert len(prof.requests_received) == 1

    clean_up()


def test_send_msg():
    from actions import signup, new_course, set_letter_quota, make_request
    from actions import send_msg
    from models import Instructor, Student, Request
    from models import STATUS_EMAILED, STATUS_REQUESTED, STATUS_DRAFTED, STATUS_FULFILLED

    prof = signup_random_user(Instructor, length=5)
    std = signup_random_user(Student, length=5)
    today = date.today()
    cs101 = new_course(code='CS101', start_date=today, course_name='Intro to CS', professor=prof)
    set_letter_quota(student=std, recommender=prof, course=cs101, quota=2)
    req = make_request(student=std, instructor=prof, course=cs101, school_applied='UC', program_applied='CS',
                       deadline=today)
    send_msg(sender=std, content='Hello, Prof.', request=req)
    req.reload()
    msg = req.messages.get()
    assert msg.sender == std.first_name + ' ' + std.last_name
    assert msg.content == 'Hello, Prof.'

    send_msg(sender="Anonymous", content='Hello, there.', request=req)
    req.reload()
    msg = req.messages.filter(sender='Anonymous').get()
    assert msg.content == 'Hello, there.'

    clean_up()


def test_fulfill_request():
    from actions import signup, new_course, set_letter_quota, make_request
    from actions import fulfill_request
    from models import Instructor, Student
    prof1 = signup_random_user(Instructor, length=5)
    prof2 = signup_random_user(Instructor, length=6)
    std = signup_random_user(Student, length=5)
    today = date.today()
    cs101 = new_course(code='CS101', start_date=today, course_name='Intro to CS', professor=prof1)
    pl101 = new_course(code='PL101', start_date=today, course_name='Politics', professor=prof2)
    set_letter_quota(student=std, recommender=prof1, course=cs101, quota=2)
    req = make_request(student=std, instructor=prof1, course=cs101, school_applied='UC', program_applied='CS',
                       deadline=today)
    reload(std, prof1, req)

    # fulfill non-related request
    with pytest.raises(DoesNotExist):
        req = fulfill_request(instructor=prof2, request=req)
    # fulfill a request
    req = fulfill_request(instructor=prof1, request=req)
    # fulfill a fulfilled request
    with pytest.raises(ActionError):
        fulfill_request(instructor=prof1, request=req)
    # fulfill a request with specific date

    tomorrow = today + timedelta(days=1)
    set_letter_quota(student=std, recommender=prof2, course=pl101, quota=2)
    req = make_request(student=std, instructor=prof2, course=pl101, school_applied='UC2', program_applied='CS2',
                       deadline=today)
    reload(std, prof2, req)
    req = fulfill_request(instructor=prof2, request=req, when=tomorrow)
    reload(std, prof2, req)
    assert req.date_fulfilled == tomorrow

    clean_up()
