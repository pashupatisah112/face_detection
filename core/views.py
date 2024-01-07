from django.shortcuts import render

def home(request):
    return render(request, 'form.html')

def folder(request):
    return render(request, 'upload_folder.html')