from django.shortcuts import render, redirect
from django.http import HttpResponse, StreamingHttpResponse, JsonResponse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from .models import Download
import yt_dlp
import requests

def index(request):
    # Si l'utilisateur est déjà connecté, on l'envoie direct sur son dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if 'download_count' not in request.session:
        request.session['download_count'] = 0
    
    context = {
        'download_count': request.session['download_count'],
        'limit_reached': request.session['download_count'] >= 3
    }
    return render(request, 'downloader/index.html', context)

@login_required
def dashboard(request):
    downloads = request.user.downloads.all()
    return render(request, 'downloader/dashboard.html', {'downloads': downloads})

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

import os
from django.conf import settings

def get_ydl_opts(format_type, quality, encoding, ydl_format):
    cookie_path = os.path.join(settings.BASE_DIR, 'cookies.txt')
    opts = {
        'format': ydl_format,
        'quiet': True,
        'merge_output_format': 'mp4' if format_type == 'mp4' else None,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }
    if os.path.exists(cookie_path):
        opts['cookiefile'] = cookie_path
    return opts

def download_video(request):
    if request.method == 'POST':
        url = request.POST.get('url')
        
        # Valeurs par défaut pour les non-membres
        format_type = 'mp4'
        quality = 'hd'
        encoding = 'iphone'
        
        # Si membre, on récupère ses choix personnalisés
        if request.user.is_authenticated:
            format_type = request.POST.get('format', 'mp4')
            quality = request.POST.get('quality', 'hd')
            encoding = request.POST.get('encoding', 'iphone')
        else:
            # Sécurité : On bloque les playlists et la limite pour les anonymes
            if 'playlist' in url or '&list=' in url:
                return HttpResponse("Playlists réservées aux membres.", status=403)
            if request.session.get('download_count', 0) >= 3:
                return HttpResponse("Limite atteinte.", status=403)

        # Configuration yt-dlp
        if format_type == 'mp3':
            ydl_format = 'bestaudio/best'
        else:
            height_limit = ""
            if quality == 'hd': height_limit = "[height<=1080]"
            elif quality == 'eco': height_limit = "[height<=480]"
            
            if encoding == 'iphone':
                ydl_format = f"bestvideo[ext=mp4][vcodec^=avc1]{height_limit}+bestaudio[ext=m4a]/best[ext=mp4]/best"
            else:
                ydl_format = f"bestvideo{height_limit}+bestaudio/best"

        ydl_opts = get_ydl_opts(format_type, quality, encoding, ydl_format)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_info = info['entries'][0] if 'entries' in info else info
                video_url = video_info.get('url')
                title = video_info.get('title', 'video')
                thumbnail = video_info.get('thumbnail')
                
                if request.user.is_authenticated:
                    Download.objects.get_or_create(
                        user=request.user, title=title, video_url=url,
                        defaults={'thumbnail_url': thumbnail, 'format_selected': f"{format_type} ({quality})"}
                    )
                else:
                    request.session['download_count'] = request.session.get('download_count', 0) + 1
                
                response = requests.get(video_url, stream=True)
                ext = 'mp3' if format_type == 'mp3' else 'mp4'
                django_response = StreamingHttpResponse(
                    response.iter_content(chunk_size=8192),
                    content_type='audio/mpeg' if format_type == 'mp3' else 'video/mp4'
                )
                django_response['Content-Disposition'] = f'attachment; filename="{title}.{ext}"'
                return django_response
                
        except Exception as e:
            return HttpResponse(f"Erreur : {str(e)}")
            
    return redirect('index')

def get_video_preview(request):
    url = request.GET.get('url')
    if not url: return JsonResponse({'error': 'URL manquante'}, status=400)
    ydl_opts = get_ydl_opts('mp4', 'hd', 'classic', 'best')
    ydl_opts.update({'noplaylist': True})
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return JsonResponse({
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration_string'),
                'view_count': info.get('view_count'),
            })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
