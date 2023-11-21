import json
import os
import cv2
import numpy as np
import random
import string
import dlib
import itertools
import dlib
import numpy as np
from skimage import io
import face_recognition
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from .settings import MEDIA_ROOT



def home(request):
    return render(request, 'form.html')


@csrf_exempt
def upload(request):
    try:
        if request.method == 'POST':
            data = request.POST

            image_file = request.FILES['image']
            random = randomGen(10)
            filename = os.path.join(MEDIA_ROOT+'/uploading', random+image_file.name)
            with open(filename, 'wb') as f:
                f.write(image_file.read())
            # savingData = {
            #     'name': data.get('name'),
            #     'email': data.get('email'),
            #     'phone': data.get('phone'),
            #     'image_url': filename
            # }
            img=cv2.imread(filename)
            # Convert the image to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Use dlib's face detector
            detector = dlib.get_frontal_face_detector()
            faces = detector(gray)
            
            existing_faces = []

            # Loop through the images in the folder
            upload_directory = os.path.join(MEDIA_ROOT, 'uploaded')
            existing_face_encoding=[]
            
            for filename in os.listdir(upload_directory):
                image_path = os.path.join(upload_directory, filename)

                # Load the existing face
                existing_image = face_recognition.load_image_file(image_path)
                existing_face_encoding.append(face_recognition.face_encodings(existing_image)[0])

            # Compare with detected faces
            for detected_face in faces:
                print('detex:', detected_face)

                #Retrieve the coordinates of the detected face rectangle
                x, y, w, h = detected_face.left(), detected_face.top(), detected_face.width(), detected_face.height()

                # Extract the face region from the image
                detected_face_image = img[y:y+h, x:x+w]

                detected_face_image_rgb = cv2.cvtColor(detected_face_image, cv2.COLOR_BGR2RGB)

                # Encode the detected face
                detected_encoding = face_recognition.face_encodings(detected_face_image_rgb)[0]

                # Compare face encodings with a threshold
                threshold = 0.6  # Adjust as needed
                match = face_recognition.compare_faces(existing_face_encoding, detected_encoding, tolerance=threshold)

                if any(match):
                    # At least one match is found
                    existing_faces.append(filename)

            print('ef:', existing_faces)
            return JsonResponse({'message': 'Data saved successfully'}, safe=False)

            

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def randomGen(length):
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string



