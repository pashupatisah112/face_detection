import os
import cv2
import dlib
from PIL import Image
import face_recognition
from datetime import datetime
from PIL import Image, ImageChops
from django.utils import timezone
from encoding.models import ImageData


def get_images_path(folder_path):
    try:
        image_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        image_paths = []

        for foldername, subfolders, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                file_extension = os.path.splitext(filename)[1].lower()

                if file_extension in image_extensions:
                    image_paths.append(file_path)
        return {'success': True, 'image_paths': image_paths}
    except Exception as e:
        return {'success': False}

def save_images_data(images, root_folder):
    try:
        data = []
        multi_face = 0
        no_face = 0
        for image in images:
            encoding = getFaceEncoding(image)
            if encoding['anomaly'] == 'multi_face':
                multi_face += 1
            elif encoding['anomaly'] == 'no_face':
                no_face += 1
            if (encoding['success'] == True):
                metadata = getImageMetadata(image, root_folder)
                data.append(
                    ImageData(
                        face_encoding=encoding['encoding'],
                        image_file_name=metadata['name'],
                        image_width=metadata['width'],
                        image_height=metadata['height'],
                        file_size=metadata['size'],
                        attributes=metadata['attributes'],
                        created_at=datetime.fromtimestamp(
                            metadata['created_at']).replace(tzinfo=timezone.utc),
                        modified_at=datetime.fromtimestamp(
                            metadata['modified_at']).replace(tzinfo=timezone.utc)
                    )
                )
        existing_combinations = ImageData.objects.values_list(
            'image_file_name', 'modified_at')

        filtered_data_to_insert = [
            row for row in data if (row.image_file_name, row.modified_at) not in existing_combinations
        ]
        saved = ImageData.objects.bulk_create(filtered_data_to_insert)
        return {'success': True, 'data': saved, 'anomaly': {'multi_face': multi_face, 'no_face': no_face}}
    except Exception as e:
        print(e)
        return {'success': False}
    
def getFaceEncoding(image):
    try:
        anomaly = ''
        img = cv2.imread(image)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        detector = dlib.get_frontal_face_detector()
        faces = detector(gray)
        if (len(faces) == 1):
            x, y, w, h = faces[0].left(), faces[0].top(
            ), faces[0].width(), faces[0].height()

            detected_face_image = img[y:y+h, x:x+w]

            detected_face_image_rgb = cv2.cvtColor(
                detected_face_image, cv2.COLOR_BGR2RGB)

            detected_encoding = face_recognition.face_encodings(
                detected_face_image_rgb)
            if len(detected_encoding) == 1:
                return {'success': True, 'encoding': detected_encoding[0], 'anomaly': None}
            else:
                return {'success': False, 'msg': 'No Face', 'anomaly': 'no-face'}
        else:
            if len(faces) > 1:
                anomaly = 'multi_face'
                msg = 'More than one face detected.'
            else:
                anomaly = 'no-face'
                msg = 'No face detected'
            return {'success': False, 'msg': msg, 'anomaly': anomaly}

    except Exception as e:
        print('Getting Face Encoding Error:', e)
        return {'success': False}
    
def getImageMetadata(image, root_folder):
    try:
        metadata = {}
        with Image.open(image) as img:
            metadata['name'] = image.split('\\')[-1]
            metadata['width'] = img.width
            metadata['height'] = img.height
            metadata['size'] = os.path.getsize(image)
            metadata['created_at'] = os.path.getctime(image)
            metadata['modified_at'] = os.path.getmtime(image)
            metadata['attributes'] = {}

            attr_path = image.split(str(root_folder+'\\'))
            att_keys = attr_path[1].split('\\')
            for i in range(0, len(att_keys)-1):
                if i == 0:
                    metadata['attributes']['attribute1'] = root_folder
                metadata['attributes']['attribute'+str(i+2)] = att_keys[i]
        return metadata
    except Exception as e:
        return {'success': False}
    
def detect_tampering(image_path, temp_path='temp_ela.jpg', quality=50):
    try:
        original = Image.open(image_path)
        original.save(temp_path, 'JPEG', quality=quality)
        saved = Image.open(temp_path)

        ela = ImageChops.difference(original, saved)
        extrema = ela.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        os.remove(temp_path)
        return 'Yes' if max_diff > 50 else 'No'
    except Exception as e:
        return f"ELA Error: {e}"

def compare_faces(existing_encoding, image_encoding):
    try:
        tolerance = 0.5
        match = face_recognition.compare_faces(
            existing_encoding, image_encoding, tolerance)
        return match
    except Exception as e:
        print(e)
        return {'success': False}
