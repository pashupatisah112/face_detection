import os
import re
import numpy as np
import math
from datetime import datetime
import requests
from core.settings import MEDIA_ROOT
from encoding.models import ImageData
from django.views.decorators.csrf import csrf_exempt
from utils.exceptions import TamperingException, FaceEncodingException, PathExtractionException
from utils.helpers import success_response, failed_response
from report.views import generate_tampering_report
from utils.views import getFaceEncoding, detect_tampering, save_images_data, get_images_path, compare_faces


@csrf_exempt
def handle_image(request):
    try:
        if request.method == 'POST':
            if (request.POST['method'] == 'url'):
                url = request.POST['url']
                response = requests.get(url, stream=True)
                uploading_path = os.path.join(
                    MEDIA_ROOT+'/uploading', os.path.basename(url))

                if response.status_code == 200:
                    with open(uploading_path, 'wb') as file:
                        for chunk in response.iter_content(chunk_size=128):
                            file.write(chunk)
            else:
                # Getting and saving image to create a temp path
                image_file = request.FILES['image']
                uploading_path = os.path.join(
                    MEDIA_ROOT+'/uploading', image_file.name)

                with open(uploading_path, 'wb') as f:
                    for chunk in image_file.chunks():
                        f.write(chunk)

            # Detecting tampering
            tampered = detect_tampering(uploading_path)
            if (tampered['success'] == False):
                raise TamperingException(tampered['msg'])

            start_time = datetime.now().timestamp()  # detecting image processing time

            face_encoding = getFaceEncoding(
                uploading_path)  # getting face encoding
            if (face_encoding['success'] == False):
                raise FaceEncodingException(face_encoding['msg'])

            duplicate_faces = []
            similar_faces = []

            existing_face_encodings = ImageData.objects.values(
                'id', 'face_encoding')

            for efe in existing_face_encodings:
                encoding = efe['face_encoding']
                existing_encoding = np.frombuffer(encoding, dtype=np.float64)
                match = compare_faces(
                    [existing_encoding], face_encoding['encoding'])

                if match['status'] == True:
                    duplicate_faces.append({
                        'id': efe['id'],
                        'percentage_match': match['percentage_match']
                    })
                else:
                    similar_faces.append({
                        'id': efe['id'],
                        'percentage_match': match['percentage_match']
                    })

            end_time = datetime.now().timestamp()

            if len(duplicate_faces) > 0:
                os.remove(uploading_path)
                return failed_response('The photo already exists.')
            else:
                save_images_data([uploading_path], '')
                os.remove(uploading_path)
                response_data = {'matched_faces': duplicate_faces, 'processig time': str(math.ceil(end_time -
                                 start_time))+'s', 'anomaly': face_encoding['anomaly'], 'tampered': tampered['data']}
                return success_response(response_data, 'Image data saved')
    except TamperingException as te:
        return failed_response(str(te))
    except FaceEncodingException as fee:
        return failed_response(str(fee))
    except Exception as e:
        print(e)
        return failed_response()


@csrf_exempt
def folder_upload(request):
    try:
        if request.method == 'POST':
            fpath = request.POST.get('fpath')
            root_folder = re.split(r'[\\//]+', fpath)[-1]

            images = get_images_path(fpath)
            if (images['success'] == False):
                raise PathExtractionException('Error geting paths of images')

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
            # generate_report({
            #     'Summary Report': report_data,
            #     'Added Data Report': addedData,
            #     'Anomaly Report': anomalies_report
            # })

            if (saved['success'] == True):
                return success_response({
                    'Summary Report': report_data,
                    'Added Data Report': addedData,
                    'Anomaly Report': anomalies_report
                })
            else:
                failed_response('Problem saving data')

    except PathExtractionException as pee:
        return failed_response(str(pee))
    except Exception as e:
        return failed_response()
