import numpy as np
from datetime import datetime
from .models import ImageData
from utils.views import compare_faces
from django.http import JsonResponse
from report.views import generate_report


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

def truncate_image_data(request):
    try:
        ImageData.objects.all().delete()
        return JsonResponse({'status': 'success', 'msg': 'Table truncated'})
    except Exception as e:
        print(e)

def cron_job(request):
    try:
        if (request.method == 'GET'):
            finalData = []
            already_matched = []
            datalist = ImageData.objects.values(
                'id', 'face_encoding', 'image_file_name', 'image_width', 'image_height', 'file_size', 'attributes', 'created_at', 'modified_at')
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
                            isim['created_at'] = datalist[j]['created_at'].strftime(
                                '%Y-%m-%d %H:%M:%S %Z')
                            isim['modified_at'] = datalist[j]['modified_at'].strftime(
                                '%Y-%m-%d %H:%M:%S %Z')
                            for k in range(0, len(datalist[j]['attributes'])):
                                for key, value in datalist[j]['attributes'].items():
                                    isim[key] = value
                            internal_sim.append(isim)
                if (len(internal_sim) > 0):
                    similarity['Match Id'] = len(finalData)+1
                    similarity['Data Id'] = datalist[i]['id']
                    similarity['Name'] = datalist[i]['image_file_name']
                    similarity['Width'] = datalist[i]['image_width']
                    similarity['Height'] = datalist[i]['image_height']
                    similarity['size'] = datalist[i]['file_size']
                    similarity['created_at'] = datalist[i]['created_at'].strftime(
                        '%Y-%m-%d %H:%M:%S %Z')
                    similarity['modified_at'] = datalist[i]['modified_at'].strftime(
                        '%Y-%m-%d %H:%M:%S %Z')
                    for k in range(0, len(datalist[i]['attributes'])):
                        for key, value in datalist[i]['attributes'].items():
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
