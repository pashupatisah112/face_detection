import os
import re
import numpy as np
import face_recognition
from datetime import datetime
from django.http import JsonResponse
from core.settings import MEDIA_ROOT
from encoding.models import ImageData
from django.views.decorators.csrf import csrf_exempt
from report.views import generate_excel_report, generate_tampering_report, generate_report
from utils.views import getFaceEncoding, detect_tampering, save_images_data, get_images_path


@csrf_exempt
def check_image_url(request):
    try:
        if request.method == 'POST':
            uploading_path = request.FILES['path']
            face_encoding = getFaceEncoding(uploading_path)
            print('fc:', face_encoding)
            return 'ok'
    except Exception as e:
        return JsonResponse({'status': False, 'detail': e})

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

                # similar_data = prepare_similarity_report(saved['data'])

                addedData = []
                for data in saved['data']:
                    dat = {}
                    dat['Data Id'] = data.id
                    dat['Name'] = data.image_file_name
                    dat['Width'] = data.image_width
                    dat['Height'] = data.image_height
                    dat['size'] = data.file_size
                    dat['created_at'] = data.created_at.strftime(
                        '%Y-%m-%d %H:%M:%S %Z')
                    dat['modified_at'] = data.modified_at.strftime(
                        '%Y-%m-%d %H:%M:%S %Z')
                    for key, value in data.attributes.items():
                        dat[key] = value
                    addedData.append(dat)

                report_data = [{
                    'Total Processing Time(s)': round(end_time-start_time, 1),
                    'Total Images Found': len(images['image_paths']),
                    'Total Images Encoded': len(saved['data']),
                    'Multi-Face Images': saved['anomaly']['multi_face'],
                    'No-Face Images': saved['anomaly']['no_face']
                }]
                generate_report({
                    'Summary Report': report_data,
                    'Added Data Report': addedData,
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
