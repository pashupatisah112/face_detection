import json
import os
import cv2
import random
import string
import dlib
import dlib
import face_recognition
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from .settings import MEDIA_ROOT

DB_PATH = os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))+'/db.json'
DB_UPLOADING = os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))+'/db.json'


def home(request):
    return render(request, 'form.html')


@csrf_exempt
def upload(request):
    try:
        if request.method == 'POST':
            data = request.POST
            image_file = request.FILES['image']
            random = randomGen(10)
            uploading_path = os.path.join(
                MEDIA_ROOT+'/uploading', random+image_file.name)
            uploaded_path = os.path.join(
                MEDIA_ROOT+'/uploaded', random+image_file.name)

            with open(uploading_path, 'wb') as f:
                for chunk in image_file.chunks():
                    f.write(chunk)
            savingData = {
                'name': data.get('fname'),
                'email': data.get('email'),
                'phone': data.get('phone'),
                'image_url': uploaded_path
            }

            img = cv2.imread(uploading_path)
            faces = detect_face(img)

            existing_face_encoding = folder_image_detect()
            compare = compare_faces(img, faces, existing_face_encoding)
            if (compare):
                os.remove(uploading_path)
                return JsonResponse({'status': 'failed', 'msg': 'Duplicate User'}, safe=False)
            else:
                with open(uploaded_path, 'wb') as f:
                    for chunk in image_file.chunks():
                        f.write(chunk)
                save_data(savingData)

            os.remove(uploading_path)
            return JsonResponse({'status': 'success', 'msg': 'Data Saved', 'data': savingData}, safe=False)

    except Exception as e:
        return JsonResponse({'status': 'failed', 'msg': 'Unknown error'}, safe=False)


def randomGen(length):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string


def compare_faces(img, faces, existing_face_encoding):
    existing_faces = []

    for detected_face in faces:
        x, y, w, h = detected_face.left(), detected_face.top(
        ), detected_face.width(), detected_face.height()

        detected_face_image = img[y:y+h, x:x+w]

        detected_face_image_rgb = cv2.cvtColor(
            detected_face_image, cv2.COLOR_BGR2RGB)

        detected_encoding = face_recognition.face_encodings(
            detected_face_image_rgb)[0]

        threshold = 0.6
        match = face_recognition.compare_faces(
            existing_face_encoding, detected_encoding, tolerance=threshold)

        if any(match):
            existing_faces.append(detect_face)
    if (len(existing_faces) > 0):
        return True
    else:
        return False


def detect_face(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    detector = dlib.get_frontal_face_detector()
    faces = detector(gray)
    return faces


def folder_image_detect():
    upload_directory = os.path.join(MEDIA_ROOT, 'uploaded')
    existing_face_encoding = []

    for filename in os.listdir(upload_directory):
        image_path = os.path.join(upload_directory, filename)
        existing_image = face_recognition.load_image_file(image_path)
        existing_face_encoding.append(
            face_recognition.face_encodings(existing_image)[0])
    return existing_face_encoding


def save_data(data):
    list = load_data()
    list.append(data)
    with open(DB_PATH, 'w') as json_file:
        json.dump(list, json_file)


def load_data():
    with open(DB_PATH, 'r') as json_file:
        data = json.load(json_file)
        return data


def data_list(request):
    try:
        with open(DB_PATH, 'r') as json_file:
            data = json.load(json_file)
            return JsonResponse({'status': 'success', 'msg': 'Data Fetched', 'data': data}, safe=False)
    except Exception as e:
        return JsonResponse({'status': 'failed', 'msg': 'Unknown error'}, safe=False)
