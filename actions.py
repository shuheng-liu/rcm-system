from datetime import date, datetime
from models import Student, Instructor, Staff, User
from models import Course, Request
from models import RequestForCourse
from models import Message
from models import STATUS_REQUESTED, STATUS_EMAILED, STATUS_DRAFTED, STATUS_FULFILLED
from passlib.hash import pbkdf2_sha256
from mongoengine import ValidationError, DoesNotExist
from err import ActionError

USER_ROLLS = [Student, Instructor, Staff]


def signup(role, email, password, first_name, last_name, gender=None):
    if role not in USER_ROLLS:
        raise RuntimeError(f"Unknown roll: {role}")
    # check for existing `email` in database
    if role.objects(email=email).count() > 0:
        raise ActionError(f"User {email} already exists")
    # hash `password`
    pwd_hash = pbkdf2_sha256.hash(password)
    # save to database
    user = role(email=email, password=pwd_hash, first_name=first_name, last_name=last_name)
    if gender:
        user.gender = gender
    return user.save()


def signin(role, email, pwd_submitted):
    # verify `email` against `password`; return the user on success
    accounts = role.objects(email=email)
    if accounts.count() == 0:
        raise ActionError(f"Incorrect username or password")
    user = accounts.first()
    if not pbkdf2_sha256.verify(pwd_submitted, user.password):
        raise ActionError(f"Incorrect username or password")
    return user


def change_password(user, old_password, password):
    # verify old password
    if not pbkdf2_sha256.verify(old_password, user.password):
        raise ActionError(f"Incorrect password")
    # update password
    user.password = pbkdf2_sha256.hash(password)
    return user.save()


def new_course(code, start_date, course_name, professor):
    course = Course(code=code, start_date=start_date, course_name=course_name, professor=professor).save()
    professor.update(add_to_set__courses=course)
    return course


def set_letter_quota(student, recommender, course, quota, reset=False):
    if quota < 0:
        raise ValidationError(f"quota={quota} is too small.")
    # register `student` to `course` if necessary
    course.update(add_to_set__students=student)

    # register `course` to `student` if necessary. Check out the following documentation
    # 1) https://stackoverflow.com/a/50658375
    # 2) https://docs.mongoengine.org/apireference.html#mongoengine.base.datastructures.EmbeddedDocumentList
    req_for_course = student.req_for_courses.filter(course=course, recommender=recommender)
    if req_for_course.count() == 0:
        student.req_for_courses.create(course=course, recommender=recommender, requests_quota=quota)
    elif reset:
        req_for_course.update(requests_quota=quota)
    else:
        raise ActionError(f"Letter quota already assigned to {recommender} for {course} exists")

    return student.save()


def reset_course_professor(course, professor, revoke_access=True):
    # revoke access to course from original professor
    if revoke_access:
        course.professor.update(pull__courses=course)
    course.update(set__professor=professor)
    professor.update(add_to_set__courses=course)
    return course


def set_course_coordinator(course, coordinator, revoke_access=True):
    # revoke access to course from original coordinator
    if revoke_access and course.coordinator is not None:
        course.coordinator.update(pull__accessible_courses=course)
    # set `course.coordinator` as `staff`
    course.update(set__coordinator=coordinator)
    coordinator.update(add_to_set__accessible_courses=course)
    return course


def assign_course_mentor(course, mentor):
    course.update(add_to_set__mentors=mentor)
    mentor.update(add_to_set__courses=course)
    return course


def withdraw_course_mentor(course, mentor, revoke_access=True):
    course.update(pull__mentors=mentor)
    if revoke_access:
        mentor.update(pull__courses=course)
    return course


def grant_access(staff, course):
    # grant to `staff` the access to `course`
    staff.update(add_to_set__accessible_courses=course)
    return staff


def revoke_access(staff, course):
    # revoke access to `course` from `staff
    staff.update(pull__accessible_courses=course)
    return staff


def make_request(student, instructor, course, school_applied, program_applied, deadline, date_created=None,
                 date_updated=None, status=STATUS_REQUESTED):
    # make a request
    req = Request(
        student=student,
        instructor=instructor,
        course=course,
        school_applied=school_applied,
        program_applied=program_applied,
        deadline=deadline,
        date_created=date_created if date_created else date.today(),
        date_updated=date_updated if date_updated else date.today(),
        status=status,
    ).save()
    # register request to student

    # Unfortunately the following is not supported
    # student.req_for_courses.\
    #     filter(course=course, recommender=instructor, requests_quota__gte=0).\
    #     update(dec__requests_quota=1, push__requests_sent=req)

    # HACK, the following is not thread-safe
    r4c = student.req_for_courses.filter(course=course, recommender=instructor).get()
    if r4c.requests_quota <= 0:
        raise DoesNotExist(f"Student {student} has no remaining quota for course {course}")
    r4c.requests_quota -= 1
    r4c.requests_sent.append(req)
    student.save()

    # register `request` to `instructor`
    instructor.update(push__requests_received=req)

    return req


def withdraw_request(student, request):
    r4c = student.req_for_courses.filter(course=request.course, recommender=request.instructor).get()
    if request in r4c.requests_sent:
        r4c.requests_sent.remove(request)
        r4c.requests_quota += 1
        student.save()
        request.delete()
    else:
        raise DoesNotExist(f"Request {request} doesn't exist")


def send_msg(sender, content, request, time=None):
    # construct a `Message` document
    if time is None:
        time = datetime.utcnow()
    msg = Message(sender=sender, content=content, time=time)
    # append to `request` Document
    request.update(push__messages=msg)


def fulfill_request(instructor, request):
    # TODO mark `request.status` as `STATUS_FULFILLED`
    pass


def view_requests(staff, by=None, vals=None):
    # TODO get all `requests` satisfying a criterion
    pass
