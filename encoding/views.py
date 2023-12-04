import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import cv2
import dlib
import face_recognition
from PIL import Image
from .models import ImageData
import re


def get_encodings(request):
    try:
        encodings = ImageData.objects.all()
        list = []
        for enc in encodings:
            list.append({
                'id': enc.id,
                'image_file_name': enc.image_file_name,
                'created_at': enc.created_at,
                'modified_at': enc.modified_at,
                'image_width': enc.image_width,
                'image_height': enc.image_height,
                'file_size': enc.file_size,
                'attributes': enc.attributes
            })
        return JsonResponse({'status': 'success', 'msg': 'Data fetched', 'data': list}, safe=False)
    except Exception as e:
        return JsonResponse({'success': False, 'msg': 'Error fetching data', 'detail': e}, safe=False)


@csrf_exempt
def folder_upload(request):
    try:
        if request.method == 'POST':
            fpath = request.POST.get('fpath')
            root_folder = re.split(r'[\\//]+', fpath)[-1]

            images = get_images_path(fpath)

            if (images['success'] == True):
                saved = save_images_data(images['image_paths'], root_folder)
                if (saved['success'] == True):
                    return JsonResponse({'status': 'success', 'msg': 'Data Saved', 'data': images}, safe=False)
                else:
                    return JsonResponse({'status': 'error', 'msg': 'Problem saving metadata', 'data': ''}, safe=False)
            else:
                return JsonResponse({'status': 'error', 'msg': 'Something wrong with folder path', 'data': ''}, safe=False)

    except Exception as e:
        return JsonResponse({'status': 'failed', 'msg': 'Unknown error', 'detail': e}, safe=False)


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
        for image in images:
            encoding = getFaceEncoding(image)
            print('enc:',encoding)
            if (encoding['success'] == True):
                metadata = getImageMetadata(image, root_folder)
                data.append(
                    ImageData(
                        face_encoding=encoding['encoding'],
                        image_file_name=metadata['name'],
                        image_width=metadata['width'],
                        image_height=metadata['height'],
                        file_size=metadata['size'],
                        attributes=metadata['attributes']
                    )
                )
        ImageData.objects.bulk_create(data)
        return {'success': True}
    except Exception as e:
        return {'success': False}


def getFaceEncoding(image):
    try:
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
                detected_face_image_rgb)[0]
            return {'success': True, 'encoding': detected_encoding}
        else:
            return {'success': False}
    except Exception as e:
        return {'success': False}


def getImageMetadata(image, root_folder):
    try:
        metadata = {}
        with Image.open(image) as img:
            metadata['name'] = image.split('\\')[-1]
            metadata['width'] = img.width
            metadata['height'] = img.height
            metadata['size'] = os.path.getsize(image)
            metadata['attributes'] = {}

            attr_path = image.split(str(root_folder+'\\'))
            att_keys = attr_path[1].split('\\')
            for i in range(0, len(att_keys)-1):
                metadata['attributes']['attribute'+str(i+1)] = att_keys[i]
        return metadata
    except Exception as e:
        return {'success': False}
