from models import Student, Instructor, Staff
from models import Course, Request
from models import Message


def signup(email, password, first_name, last_name, gender=None, role=None):
    # TODO verify `email` is not present in database
    pass
    # TODO hash `password`
    pass
    # TODO save to database
    pass


def signin(email, pwd_submitted, role=None):
    # TODO verify `email` against `password`; returns True/False
    pass


def change_password(user, old_password, password, role=None):
    # TODO verify old password
    pass
    # TODO update password
    pass


def enroll(course, student):
    # TODO register `student` to `course`
    pass
    # TODO register `course` to `student`
    pass


def new_course(code, start_date, course_name, professor):
    # TODO instantiate a new course
    pass


def set_professor(instructor, course):
    # TODO set `course.professor` as `insturcotr`
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