import cv2
import os
from flask import Flask,request,render_template,session,redirect,url_for
from datetime import date
from datetime import datetime
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
import pandas as pd
import joblib
import mysql.connector


#### Defining Flask App
app = Flask(__name__)
app.secret_key='super secret key'




# database


mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  database="face_db"
)
cursor = mydb.cursor()
cursor.execute("SELECT * FROM users ")

    # Get the results and convert them to JSON
results = cursor.fetchall()
print(results)
# cursor.execute("INSERT INTO `users`(`Username`, `Password`, `Email`) VALUES ('lokesh','lokesh','lok@gmail.com')")





datetoday = date.today().strftime("%m_%d_%y")
datetoday2 = date.today().strftime("%d-%B-%Y")


#### Initializing VideoCapture object to access WebCam
face_detector = cv2.CascadeClassifier('static/haarcascade_frontalface_default.xml')
cap = cv2.VideoCapture(0)



if not os.path.isdir('Attendance'):
    os.makedirs('Attendance')
if not os.path.isdir('static/faces'):
    os.makedirs('static/faces')
if f'Attendance-{datetoday}.csv' not in os.listdir('Attendance'):
    with open(f'Attendance/Attendance-{datetoday}.csv','w') as f:
        f.write('Name,Roll,Time')



def totalreg():
    return len(os.listdir('static/faces'))


def extract_faces(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_points = face_detector.detectMultiScale(gray, 1.3, 5)
    return face_points


def identify_face(facearray):
    model = joblib.load('static/face_recognition_model.pkl')
    return model.predict(facearray)


def train_model():
    faces = []
    labels = []
    userlist = os.listdir('static/faces')
    for user in userlist:
        for imgname in os.listdir(f'static/faces/{user}'):
            img = cv2.imread(f'static/faces/{user}/{imgname}')
            resized_face = cv2.resize(img, (50, 50))
            faces.append(resized_face.ravel())
            labels.append(user)
    faces = np.array(faces)
    knn = KNeighborsClassifier(n_neighbors=5)
    knn.fit(faces,labels)
    joblib.dump(knn,'static/face_recognition_model.pkl')


#### Extract info from today's attendance file in attendance folder
def extract_attendance():
    df = pd.read_csv(f'Attendance/Attendance-{datetoday}.csv')
    names = df['Name']
    rolls = df['Roll']
    times = df['Time']
    l = len(df)
    return names,rolls,times,l


def add_attendance(name):
    username = name.split('_')[0]
    userid = name.split('_')[1]
    current_time = datetime.now().strftime("%H:%M:%S")
    
    df = pd.read_csv(f'Attendance/Attendance-{datetoday}.csv')
    if int(userid) not in list(df['Roll']):
        with open(f'Attendance/Attendance-{datetoday}.csv','a') as f:
            f.write(f'\n{username},{userid},{current_time}')





@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login',methods=['GET','POST'])
def login():
    
    print("CALLED")
    if request.method == 'POST':

        username = request.form['Username']
        password = request.form['Password']
        print(username)

        cursor.execute("SELECT * FROM users WHERE Username = %s AND Password = %s",(username,password))
        record=cursor.fetchone()
        if record:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('home'))
            
        else:
            msg='Incorrect username or password'
    return render_template('index.html',msg=msg)




@app.route('/home')
def home():
    if not session['logged_in']:
        msg='You are not logged in'
        return render_template('index.html',msg=msg)

    names,rolls,times,l = extract_attendance()    
    return render_template('home.html',names=names,rolls=rolls,times=times,l=l,totalreg=totalreg(),datetoday2=datetoday2,username=session['username'])


@app.route("/register",methods=['GET','POST'])
def register():
    
    msg=''
    if request.method == 'POST':
        print("POST REGISTER CALLED")

        username = request.form['Username']
        password = request.form['Password']
        email = request.form['email']
        print(username)
        print(password)
        print(email)
        cursor.execute("SELECT * FROM users WHERE Username = %s AND Password = %s",(username,password))
        record=cursor.fetchone()
        if record:
            msg='Username already exists'
            return render_template('index.html',msg=msg)

        cursor.execute("INSERT INTO `users`(`Username`, `Password`, `Email`) VALUES (%s,%s,%s)",(username,password,email))
        mydb.commit()
        msg="user registered successfully"

        return redirect(url_for('login'))
    return render_template('index.html',msg=msg)


        


@app.route('/logout')
def logout():
    session.pop('logged_in',None)
    session.pop('username',None)
    return redirect(url_for('index'))


#### This function will run when we click on Take Attendance Button
@app.route('/start',methods=['GET'])
def start():
    if not session['logged_in']:
        msg='You are not logged in'
        return render_template('index.html',msg=msg)
    if 'face_recognition_model.pkl' not in os.listdir('static'):
        return render_template('home.html',totalreg=totalreg(),datetoday2=datetoday2,mess='There is no trained model in the static folder. Please add a new face to continue.') 

    cap = cv2.VideoCapture(0)

    print('cap==' + str(cap))

    ret = True
    while ret:
        print('called')
        ret,frame = cap.read()
        if extract_faces(frame)!=():
            (x,y,w,h) = extract_faces(frame)[0]
            cv2.rectangle(frame,(x, y), (x+w, y+h), (255, 0, 20), 2)
            face = cv2.resize(frame[y:y+h,x:x+w], (50, 50))
            identified_person = identify_face(face.reshape(1,-1))[0]
            add_attendance(identified_person)
            cv2.putText(frame,f'{identified_person}',(30,30),cv2.FONT_HERSHEY_SIMPLEX,1,(255, 0, 20),2,cv2.LINE_AA)
            cv2.imshow('Attendance',frame)
        if cv2.waitKey(1)==27:
            break
    cap.release()
    cv2.destroyAllWindows()
    names,rolls,times,l = extract_attendance()    
    return render_template('home.html',names=names,rolls=rolls,times=times,l=l,totalreg=totalreg(),datetoday2=datetoday2) 


#### This function will run when we add a new user
@app.route('/add',methods=['GET','POST'])
def add():
    if not session['logged_in']:
        msg='You are not logged in'
        return render_template('index.html',msg=msg)
    newusername = request.form['newusername']
    newuserid = request.form['newuserid']
    userimagefolder = 'static/faces/'+newusername+'_'+str(newuserid)
    if not os.path.isdir(userimagefolder):
        os.makedirs(userimagefolder)
    cap = cv2.VideoCapture(0)
    i,j = 0,0
    while 1:
        _,frame = cap.read()
        faces = extract_faces(frame)
        print(len(faces))
        for (x,y,w,h) in faces:
            cv2.rectangle(frame,(x, y), (x+w, y+h), (255, 0, 20), 2)
            cv2.putText(frame,f'Images Captured: {i}/50',(30,30),cv2.FONT_HERSHEY_SIMPLEX,1,(255, 0, 20),2,cv2.LINE_AA)
            if j%10==0:
                name = newusername+'_'+str(i)+'.jpg'
                print(name)
                cv2.imwrite(userimagefolder+'/'+name,frame[y:y+h,x:x+w])
                i+=1
            j+=1
        if i==50:
            break
        cv2.imshow('Adding new User',frame)
        if cv2.waitKey(1)==27:
            print("BREAKKKKKKKKKKK")
            break
    cap.release()
    cv2.destroyAllWindows()
    print('Training Model')
    train_model()
    names,rolls,times,l = extract_attendance()    
    return render_template('home.html',names=names,rolls=rolls,times=times,l=l,totalreg=totalreg(),datetoday2=datetoday2) 


if __name__ == '__main__':
    app.run(debug=True)