from models import Student, Instructor, Staff, User
from models import Course, Request
from models import Message
from passlib.hash import pbkdf2_sha256
from err import ActionError

USER_ROLLS = [Student, Instructor, Staff]


def signup(role, email, password, first_name, last_name, gender=None):
    if role not in USER_ROLLS:
        raise RuntimeError(f"Unknown roll: {role}")
    # check for existing `email` in database
    if role.objects(email=email).count() > 0:
        raise ActionError(f"User {email} already exists")
    # hash `password`
    pwd_hash = pbkdf2_sha256.encrypt(password)
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
    user.password = pbkdf2_sha256.encrypt(password)
    return user.save()


def enroll(course, student):
    # TODO register `student` to `course`
    pass
    # TODO register `course` to `student`
    pass


def new_course(code, start_date, course_name, professor):
    return Course(code=code, start_date=start_date, course_name=course_name, professor=professor).save()


def set_professor(instructor, course):
    # TODO set `course.professor` as `instructor`
    pass


def set_coordinator(staff, course):
    # TODO set `course.coordinator` as `staff`
    pass


def append_mentor(instructor, course):
    # TODO check whether `instructor` exists in `course.mentor` first
    pass


def grant_access(staff, course):
    # TODO grant to `staff` the access to `course`
    pass


def make_request(student, instructor, course, school_applied, program_applied, deadline):
    # TODO make a `request`
    pass
    # TODO register `request` to `student`
    pass
    # TODO register `request` to `instructor`
    pass


def update_request(request, student=None, instructor=None, course=None, school_applied=None, program_applied=None,
                   deadline=None):
    # TODO update `request` and save
    pass


def send_msg(sender, content, request):
    # TODO construct a `Message` document
    pass
    # TODO append to `request` Document


def fulfill_request(instructor, request):
    # TODO mark `request.status` as `STATUS_FULFILLED`
    pass


def view_requests(staff, by=None, vals=None):
    # TODO get all `requests` satisfying a criterion
    pass
