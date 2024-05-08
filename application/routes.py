from application import app, db
from flask import request, jsonify, g
import jwt
from application.middleware import authorization
import uuid
from datetime import datetime, timedelta, timezone
import re

@app.route('/')
def index():
    return "Hello zworld"

app.config['SECRET_KEY'] = '815d6db856'

@app.route('/add_student', methods=["POST"])
def add_student():
    data = request.json
    if not "faculty" in data or not "name" in data or not "surname" in data or not "password" in data:
        return jsonify({"message":"please fill all the info"}), 400
    data["index"] = str(uuid.uuid4())[0:4]
    data["semester"] = 1
    data["role"] = "student"
    data["inbox"] = []
    data["outbox"] = []
    faculty = db.faculties.find_one({"name":data["faculty"]})
    grades = []
    for x in faculty["subjects"]:
        grades.append({"name":x, "grade": 0, "activity":[]})
    attendance = []
    for x in faculty["subjects"]:
        attendance.append({"subject":x, "attendance":100})
    db.grades.insert_one({"name":data["name"],"surname":data["surname"],"index": data["index"], "grades":grades, "attendance":attendance})
    db.students.insert_one(data.copy())
    return jsonify({"message":"student added", "newStudent":data}), 201

@app.route('/add_teacher', methods=["POST"])
def add_teacher():
    data = request.json
    print(data)
    if not "name"in data or not "surname"in data or not "subjects"  in data or not 'password' in data:
        return jsonify({"message":"please fill all the info"})
    data['subjects'] = data['subjects'].split(',')
    data['index'] = str(uuid.uuid4())[0:4]
    data["role"] = "teacher"
    data["inbox"] = []
    data["outbox"] = []
    db.teachers.insert_one(data)
    return jsonify({"message":"teacher added"}), 201


@app.route('/login', methods=["POST"])
def login():
    data = request.json
    if not "index" in data or not "password" in data:
        return jsonify({"message":"bad request"}), 400
    query = {"index":data["index"], "password":data["password"]}
    user = db.students.find_one(query)
    teacher = db.teachers.find_one(query)
    if not user and not teacher:
        return jsonify({"message":"incorrect name or password"}), 400
    expiration_time = datetime.now(timezone.utc) + timedelta(days=30)
    token = jwt.encode({
        "index": data["index"],
        "expiration":expiration_time.timestamp()
    }, app.config['SECRET_KEY'])
    if user:
        return jsonify({"token" : token, "name":user["name"], "role":"student"}), 200
    elif teacher:
        return jsonify({"token" : token, "name":teacher["name"], "role":"teacher"}), 200


@app.route('/add_faculty', methods=['POST'])
def add_faculty():
    data = request.json
    if not "name" in data or not "subjects" in data or not "timeTable" in data:
        return jsonify({"message":"please provide all the data"}),401
    current_date_time = datetime.now()
    formatted_date_time = current_date_time.strftime("%A, %B %d, %Y")
    material = [{"subject":"math", "title":"new homework", "text":"something something", "time": str(formatted_date_time)}]
    data["material"] = material
    db.faculties.insert_one(data)
    return jsonify({"message":"faculty created"}), 201

@app.route('/add_news', methods=['POST'])
def add_news():
    data = request.json
    if not "type" in data or not "title" in data or not "text" in data:
        return jsonify({'message':"please provide all the data needed"}), 401
    current_date_time = datetime.now()
    formatted_date_time = current_date_time.strftime("%A, %B %d, %Y")
    data["time"] = str(formatted_date_time)
    db.news.insert_one(data.copy())
    return jsonify({"message":"news shared", "new":data})
    
@app.route('/send_mail', methods=['POST'])
@authorization
def send_mail():
    data = request.json
    if not "index" or not "text" in data or not "subject" in data  or not "type" in data:
        return jsonify({"message":"please provide all the info"}), 401
    if data["type"] == 0:
        sender = db.students
        receiver = db.teachers
        person = db.students.find_one({'index':g.token['index']})
        data['from'] = person['name']+ ' ' + person['surname']
    else:
        sender = db.teachers
        receiver = db.students
        person = db.teachers.find_one({'index':g.token['index']})
        data['from'] = person['name']+ ' ' + person['surname']
    current_date_time = datetime.now()
    formatted_date_time = current_date_time.strftime("%A, %B %d, %Y")
    person1 = receiver.find_one({"index": data['index']})
    newInbox1= []
    newInbox1.append({"from":data["from"], "subject":data["subject"], "text":data["text"], "time":str(formatted_date_time)})
    for x in person1["inbox"]:
        newInbox1.append(x)
    receiver.update_one({"index":data['index']}, {"$set":{"inbox":newInbox1}})
    person2 = sender.find_one({"index":g.token['index']})
    newOutbox1 = []
    newOutbox1.append({"from":person1['name'] + ' ' + person1['surname'], "subject":data["subject"], "text":data["text"], "time":str(formatted_date_time)})
    for x in person2["outbox"]:
        newOutbox1.append(x)
    sender.find_one_and_update({"index":g.token['index']}, {"$set": {"outbox" : newOutbox1}})
    return jsonify({"message":"message sent",'mail':{"from":person1['name'] + ' ' + person1['surname'], "subject":data["subject"], "text":data["text"], "time":str(formatted_date_time)}}), 201


@app.route('/home', methods=["GET"])
@authorization
def home():
    student = db.students.find_one({"index":g.token["index"]})
    if not student:
        news = list(db.news.find({}))
        for x in news:
            x.pop('_id', None)
        teacher=  db.teachers.find_one({"index":g.token['index']})
        teacher.pop('_id', None)
        return jsonify(news,teacher)
    student.pop("_id", None)
    facultyNews = list(db.news.find({"type":"faculty"}))
    for x in facultyNews:
        x.pop('_id', None)
    fieldNews = list(db.news.find({"type":student["faculty"]}))
    for x in fieldNews:
        x.pop('_id', None)
    return jsonify({"card":student, "facultyNews":facultyNews, "fieldNews":fieldNews})

@app.route('/timetable', methods=["GET"])
@authorization
def timeTable():
    student = db.students.find_one({"index":g.token["index"]})
    if not student:
        subjects = db.teachers.find_one({'index':g.token["index"]})['subjects']
        faculties = db.faculties.find({})
        timeTable = {"monday":[], "tuesday":[],"wednesday":[],"thursday":[],"friday":[]}
        for x in faculties:
            for y in x['timeTable']:
                for z in x['timeTable'][y]:
                    if z['subject'] in subjects:
                        timeTable[y].append(z)
        return jsonify(timeTable), 200
    faculty = db.faculties.find_one({"name":student["faculty"]})
    return jsonify(faculty["timeTable"]), 200

@app.route('/attendance', methods=["GET"])
@authorization
def attendance():
    attendance = db.grades.find_one({"index":g.token["index"]})["attendance"]
    return jsonify(attendance), 200

@app.route('/grades', methods=['GET'])
@authorization
def grades():
    grades = db.grades.find_one({"index":g.token["index"]})
    return jsonify(grades["grades"]),200

@app.route('/subjects', methods=['GET'])
@authorization
def subjects():
    student = db.students.find_one({"index":g.token["index"]})
    faculty = db.faculties.find_one({'name':student["faculty"]})
    return jsonify({"subjects":faculty["subjects"], "material":faculty["material"]})

@app.route('/teachers', methods=['GET'])
@authorization
def teachers():
    if not db.students.find_one({'index':g.token['index']}):
        senders = db.students.find()
    else:
        senders = list(db.teachers.find())
    filteredSenders = []
    for x in senders:
        filteredSenders.append({"index":x["index"], "name":x['name'], "surname":x["surname"]})
    return jsonify(filteredSenders), 200

@app.route('/mails', methods=['GET'])
@authorization
def mails():
    mails = db.students.find_one({"index":g.token["index"]})
    if not mails:
        mails = db.teachers.find_one({"index":g.token["index"]})
    return jsonify({"inbox":mails["inbox"], "outbox":mails["outbox"]}), 200

@app.route('/searchSenders', methods=['GET'])
def search():
    type = int(request.args.get('type'))
    term = request.args.get('term')
    regex_pattern = re.compile(f'.*{re.escape(term)}.*', re.IGNORECASE)
    if type == 0 :
        search = db.students.find({"name": {"$regex": regex_pattern}})
    else:
        search = db.teachers.find({"name": {"$regex": regex_pattern}})
    results = []
    for x in search:
        results.append({"index":x["index"], "name":x['name'], "surname":x["surname"]})
    return jsonify(results)
@app.route('/get_students', methods=['GET'])
def students():
    term = request.args.get('term')
    result = []
    if not term:
        students = list(db.students.find({}))
        for x in students:
            result.append({'name':x['name'], 'surname':x['surname'],'index':x['index'], 'semester':x['semester'],'faculty':x['faculty']})
        return jsonify(result)
    regex_pattern = re.compile(f'.*{re.escape(term)}.*', re.IGNORECASE)
    search = db.students.find({"name": {"$regex": regex_pattern}})
    for x in search:
        result.append({'name':x['name'], 'surname':x['surname'],'index':x['index'], 'semester':x['semester'],'faculty':x['faculty']})
    return jsonify(result)

@app.route('/get_faculties', methods=['GET'])
def faculties():
    faculties = list(db.faculties.find())
    result = []
    for x in faculties:
        result.append(x['name'])
    return jsonify(result)
@app.route('/get_student', methods=['GET'])
def student():
    index = request.args.get('index')
    student = db.grades.find_one({'index':index})
    return jsonify({'grades':student['grades'], 'attendance':student['attendance'], "name":student['name'], "surname":student['surname'], "index":index})
@app.route('/update_student', methods=['PATCH'])
def update_grade():
    data= request.json
    print(data)
    student = db.grades.find_one({'index':data['index']})
    newGrades = []
    for x in student['grades']:
        if x['name'] == data['newGrade']['name']:
            newGrades.append(data['newGrade'])
        else:
            newGrades.append(x)
    db.grades.find_one_and_update({'index':data['index']},{"$set":{'grades':newGrades}})
    return jsonify({'message':'success'})
@app.route('/edit_attendance', methods=['PATCH'])
def edit_att():
    data =request.json
    db.grades.find_one_and_update({'index':data['index']},{"$set":{'attendance':data['data']}})
    return jsonify({'message':'student updated'})


@app.route('/add_material', methods=['PATCH'])
def add_material():
    data = request.json
    if not "subject" in data or not 'title' in data or not "text" in data:
        jsonify({"message":'please fill all the info'}),400
    faculties = db.faculties.find()
    current_date_time = datetime.now()
    formatted_date_time = current_date_time.strftime("%A, %B %d, %Y")
    for x in faculties:
        if data['subject'] in x['subjects']:
            newMaterial = []
            newMaterial.append({'subject':data['subject'], "title":data['title'], "text":data['text'], 'time':formatted_date_time})
            for y in x['material']:
                newMaterial.append(y)
            db.faculties.find_one_and_update({'name':x['name']}, {"$set":{'material':newMaterial}})
    return jsonify({'message':'material added'})

@app.route('/get_subjects', methods=['GET'])
@authorization
def teacher_subjects():
    subjects = db.teachers.find_one({'index':g.token['index']})['subjects']
    return jsonify(subjects), 200

@app.route('/remove', methods=['PATCH'])
def remove():
    data = request.json
    student = db.students.find_one({'index':data['data']})
    teacher = db.teachers.find_one({'index':data['data']})
    if student:
        db.students.find_one_and_delete({'index':data['data']})
    elif teacher:
        db.teachers.find_one_and_delete({'index':data['data']})
    else:
        return jsonify({'message':'user not found'}),400
    return jsonify({'message':"user removed"})

@app.route('/getTimeTables', methods=['GET'])
def get_tt():
    faculties = db.faculties.find()
    tt = []
    for x in faculties:
        tt.append({'name':x['name'], 'tt':x['timeTable'], 'subjects':x['subjects']})
    return jsonify(tt),200

@app.route('/edit_tt', methods=['PATCH'])
def edit_tt():
    data= request.json
    db.faculties.find_one_and_update({'name':data['name']}, {'$set':{"timeTable":data['tt']}})
    return jsonify({'message':"timeTable updated"})