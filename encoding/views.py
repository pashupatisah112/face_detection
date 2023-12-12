import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import cv2
import dlib
import face_recognition
from PIL import Image
from .models import ImageData
import re
from core.settings import MEDIA_ROOT
import numpy as np
import pandas as pd
from datetime import datetime
from PIL import Image, ImageChops, ImageFilter


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
def check_image(request):
    try:
        if request.method == 'POST':
            image_file = request.FILES['image']
            uploading_path = os.path.join(
                MEDIA_ROOT+'/uploading', image_file.name)

            with open(uploading_path, 'wb') as f:
                for chunk in image_file.chunks():
                    f.write(chunk)

            tampered = detect_tampering(uploading_path)
            start_time = datetime.now().timestamp()
            face_encoding = getFaceEncoding(uploading_path)
            if (face_encoding['success'] == True):
                threshold = 0.5
                duplicate_faces = []
                similar_faces = []
                existing_face_encodings = ImageData.objects.values(
                    'id', 'face_encoding')
                for efe in existing_face_encodings:
                    encoding = efe['face_encoding']
                    existing_encoding = np.frombuffer(
                        encoding, dtype=np.float64)
                    match = face_recognition.compare_faces(
                        [existing_encoding], face_encoding['encoding'], tolerance=threshold)

                    if match[0]:
                        duplicate_faces.append({
                            'id': efe['id'],
                            'percentage_match': 100.0,
                        })
                    else:
                        similarity = face_recognition.face_distance(
                            [existing_encoding], face_encoding['encoding'])
                        similarity_percentage = (1 - similarity[0]) * 100

                        if similarity_percentage > threshold and similarity_percentage >= 50:
                            similar_faces.append({
                                'id': efe['id'],
                                'percentage_match': similarity_percentage,
                            })
                end_time = datetime.now().timestamp()

                if len(duplicate_faces) > 0:
                    os.remove(uploading_path)
                    generate_excel_report(
                        duplicate_faces, end_time-start_time, face_encoding['anomaly'], tampered)
                    return JsonResponse({'status': 'failed', 'msg': 'Duplicate User'})
                else:
                    save_images_data(uploading_path, 'New')
                    os.remove(uploading_path)
                    return JsonResponse({'status': 'success', 'msg': 'Image data saved'})
            else:
                return JsonResponse({'status': 'failed', 'msg': 'Unexpected error'})
    except Exception as e:
        return JsonResponse({'status': False, 'detail': e})


@csrf_exempt
def folder_upload(request):
    try:
        if request.method == 'POST':
            fpath = request.POST.get('fpath')
            root_folder = re.split(r'[\\//]+', fpath)[-1]

            images = get_images_path(fpath)

            if (images['success'] == True):
                start_time = datetime.now().timestamp()
                saved = save_images_data(images['image_paths'], root_folder)
                anomalies_report = generate_tampering_report(
                    images['image_paths'], saved['data'])
                end_time = datetime.now().timestamp()

                similar_data = prepare_similarity_report(saved['data'])

                report_data = [{
                    'Total Processing Time(s)': round(end_time-start_time, 1),
                    'Total Images Found': len(images['image_paths']),
                    'Total Images Encoded': len(saved['data']),
                    'Multi-Face Images': saved['anomaly']['multi_face'],
                    'No-Face Images': saved['anomaly']['no_face']
                }]
                generate_report({
                    'Summary Report': report_data,
                    'Similarity Report': [similar_data],
                    'Anomaly Report': anomalies_report
                })

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
                        attributes=metadata['attributes']
                    )
                )
        saved = ImageData.objects.bulk_create(data)
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


def truncate_image_data(request):
    try:
        ImageData.objects.all().delete()
        return JsonResponse({'status': 'success', 'msg': 'Table truncated'})
    except Exception as e:
        print(e)


def generate_excel_report(image_data, time, anomaly, tampered):
    try:
        ids = []
        for img in image_data:
            ids.append(img['id'])
        img_data = ImageData.objects.filter(id__in=ids)

        finalData = []
        for data in img_data:
            dat = {}
            dat['id'] = data.id
            dat['image_file_name'] = data.image_file_name
            dat['image_height(px)'] = data.image_height
            dat['image_width(px)'] = data.image_width
            dat['file_size(bytes)'] = data.file_size
            finalData.append(dat)

        duplicate = False
        if (len(finalData) > 0):
            duplicate = True

        summaryData = [
            {'Total Image Processing Time(s)': round(time, 1), 'Is Duplicate': duplicate, 'Anomaly': anomaly, 'Tampered': tampered}]
        generate_report({
            'Summary Report': summaryData,
            'Similarity Report': finalData
        })

    except Exception as e:
        print(e)
        return JsonResponse({'status': 'failed', 'msg': e})


def generate_report(dataset):
    time = str(datetime.now().timestamp())
    with pd.ExcelWriter('report '+time+'.xlsx', engine='openpyxl') as writer:
        for sheet_name, data in dataset.items():
            df = pd.DataFrame(data)
            if (len(data) == 1):
                df = df.transpose()
                df.reset_index(inplace=True)
                if (sheet_name == 'Summary Report'):
                    df.columns = ['Title', 'Value']
                elif (sheet_name == 'Similarity Report'):
                    df.columns = ['Image Id', 'Similar Id']
            df.to_excel(writer, index=False, sheet_name=sheet_name)


def prepare_similarity_report(datalist):
    try:
        similarity = {}
        for i in range(0, len(datalist)):
            selected = datalist[i]
            similar_ids = ''
            for j in range(0, len(datalist)):
                if (j != i):
                    match = compare_faces(
                        [datalist[j].face_encoding], selected.face_encoding)
                    if match[0]:
                        if (similar_ids):
                            similar_ids += ','
                        similar_ids += str(datalist[j].id)
            similarity[selected.id] = similar_ids
        return similarity
    except Exception as e:
        print(e)
        return {'success': False}


def compare_faces(existing_encoding, image_encoding):
    try:
        tolerance = 0.5
        match = face_recognition.compare_faces(
            existing_encoding, image_encoding, tolerance)
        return match
    except Exception as e:
        print(e)
        return {'success': False}


def cron_job(request):
    try:
        if (request.method == 'GET'):
            finalData = []
            already_matched = []
            datalist = ImageData.objects.values(
                'id', 'face_encoding', 'image_file_name', 'image_width', 'image_height', 'file_size', 'attributes')
            start_time = datetime.now().timestamp()
            for i in range(0, len(datalist)):
                selected = np.frombuffer(
                    datalist[i]['face_encoding'], dtype=np.float64)
                similarity = {}
                internal_sim = []
                for j in range(0, len(datalist)):
                    if (j != i and datalist[i]['id'] not in already_matched):

                        existing_encoding = np.frombuffer(
                            datalist[j]['face_encoding'], dtype=np.float64)
                        match = compare_faces(
                            [existing_encoding], selected)

                        if match[0]:
                            isim = {}
                            already_matched.append(datalist[j]['id'])
                            isim['Match Id'] = len(finalData)+1
                            isim['Data Id'] = datalist[j]['id']
                            isim['Name'] = datalist[j]['image_file_name']
                            isim['Width'] = datalist[j]['image_width']
                            isim['Height'] = datalist[j]['image_height']
                            isim['size'] = datalist[j]['file_size']
                            for k in range(0, len(datalist[j]['attributes'])):
                                for key,value in datalist[j]['attributes'].items():
                                    isim[key] = value
                            internal_sim.append(isim)
                if (len(internal_sim) > 0):
                    similarity['Match Id'] = len(finalData)+1
                    similarity['Data Id'] = datalist[i]['id']
                    similarity['Name'] = datalist[i]['image_file_name']
                    similarity['Width'] = datalist[i]['image_width']
                    similarity['Height'] = datalist[i]['image_height']
                    similarity['size'] = datalist[i]['file_size']
                    for k in range(0, len(datalist[i]['attributes'])):
                        for key,value in datalist[i]['attributes'].items():
                            similarity[key] = value
                    internal_sim.append(similarity)
                    finalData.extend(internal_sim)

            end_time = datetime.now().timestamp()
            
            report_data = [{
                'Total Processing Time(s)': round(end_time-start_time, 1),
                'Total Images Found': len(datalist),
                'Multi-Face Images': 0,
                'No-Face Images': 0
            }]
            generate_report({
                'Summary Report': report_data,
                'Similarity Report': finalData
            })
            return JsonResponse({'status': 'success', 'msg': 'Cron job started successfully'}, safe=False)
    except Exception as e:
        print(e)
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


def generate_tampering_report(paths, saved):
    try:
        tampering_data = []
        for i in range(0, len(saved)):
            data = {'id': saved[i].id}
            data['tampered'] = detect_tampering(paths[i])
            tampering_data.append(data)
        return tampering_data
    except Exception as e:
        return
