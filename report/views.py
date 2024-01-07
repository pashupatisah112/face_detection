from encoding.models import ImageData
from datetime import datetime
import pandas as pd
from utils.views import compare_faces, detect_tampering

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
            dat['created_at'] = data.created_at.strftime(
                '%Y-%m-%d %H:%M:%S %Z')
            dat['modified_at'] = data.modified_at.strftime(
                '%Y-%m-%d %H:%M:%S %Z')
            for key, value in data.attributes.items():
                dat[key] = value
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
        return False

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
