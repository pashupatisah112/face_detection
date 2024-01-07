from django.http import JsonResponse


def success_response(data=[], msg='Request Completed'):
    return JsonResponse({'status': 'Success', 'data': data, 'msg': msg})


def failed_response(msg='Unxepected Error'):
    return JsonResponse({'status': 'Failed', 'msg': msg})
