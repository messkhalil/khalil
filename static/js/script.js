document.addEventListener('DOMContentLoaded', function() {
    // العناصر الرئيسية
    const videoUrlInput = document.getElementById('videoUrl');
    const searchBtn = document.getElementById('searchBtn');
    const loader = document.getElementById('loader');
    const errorContainer = document.getElementById('errorContainer');
    const errorMessage = document.getElementById('errorMessage');
    const videoContainer = document.getElementById('videoContainer');
    const downloadProgress = document.getElementById('downloadProgress');
    
    // معلومات الفيديو
    const thumbnail = document.getElementById('thumbnail');
    const videoTitle = document.getElementById('videoTitle');
    const videoAuthor = document.getElementById('videoAuthor');
    const videoViews = document.getElementById('videoViews');
    const videoDate = document.getElementById('videoDate');
    const videoDuration = document.getElementById('videoDuration');
    
    // قوائم التنسيقات
    const videoFormats = document.getElementById('videoFormats');
    const audioFormats = document.getElementById('audioFormats');
    
    // تنسيق المدة الزمنية
    function formatDuration(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const remainingSeconds = seconds % 60;
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
        }
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    // التبديل بين علامات التبويب
    document.querySelectorAll('.tab-btn').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            button.classList.add('active');
            document.getElementById(button.dataset.tab + 'Tab').classList.add('active');
        });
    });

    // إظهار وإخفاء عناصر واجهة المستخدم
    function showLoader() {
        loader.style.display = 'flex';
        videoContainer.style.display = 'none';
        errorContainer.style.display = 'none';
        downloadProgress.style.display = 'none';
    }

    function hideLoader() {
        loader.style.display = 'none';
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorContainer.style.display = 'block';
        videoContainer.style.display = 'none';
        downloadProgress.style.display = 'none';
    }

    function createFormatItem(format, type) {
        const div = document.createElement('div');
        div.className = 'format-item';
        
        let qualityText, detailsText;
        if (type === 'video') {
            qualityText = `${format.resolution} - ${format.mime_type.toUpperCase()}`;
            detailsText = `${format.fps} FPS - ${format.filesize}`;
        } else {
            qualityText = `${format.abr} - ${format.mime_type.toUpperCase()}`;
            detailsText = format.filesize;
        }

        div.innerHTML = `
            <div class="format-info">
                <span class="format-quality">${qualityText}</span>
                <span class="format-details">${detailsText}</span>
            </div>
            <button class="download-btn" data-itag="${format.itag}" data-type="${type}">
                <i class="fas fa-download"></i> تحميل
            </button>
        `;
        
        return div;
    }

    function displayVideoInfo(data) {
        // عرض معلومات الفيديو
        thumbnail.src = data.thumbnail;
        videoTitle.textContent = data.title;
        videoAuthor.textContent = data.author;
        videoViews.textContent = data.views;
        videoDate.textContent = data.publish_date || 'غير متوفر';
        videoDuration.textContent = formatDuration(data.length);

        // عرض تنسيقات الفيديو
        videoFormats.innerHTML = '';
        data.video_streams.forEach(format => {
            videoFormats.appendChild(createFormatItem(format, 'video'));
        });

        // عرض تنسيقات الصوت
        audioFormats.innerHTML = '';
        data.audio_streams.forEach(format => {
            audioFormats.appendChild(createFormatItem(format, 'audio'));
        });

        // إظهار حاوية الفيديو
        videoContainer.style.display = 'block';
        errorContainer.style.display = 'none';
        downloadProgress.style.display = 'none';
    }

    async function startDownload(url, itag, type) {
        try {
            downloadProgress.style.display = 'block';
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url, itag, type })
            });

            const data = await response.json();

            if (response.ok) {
                // إنشاء رابط التحميل وتفعيله تلقائياً
                const link = document.createElement('a');
                link.href = data.download_url + '?name=' + encodeURIComponent(data.filename);
                link.style.display = 'none';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                downloadProgress.style.display = 'none';
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            showError(error.message);
        }
    }

    // معالجة النقر على زر البحث
    searchBtn.addEventListener('click', async () => {
        const url = videoUrlInput.value.trim();
        
        if (!url) {
            showError('الرجاء إدخال رابط الفيديو');
            return;
        }

        showLoader();

        try {
            const response = await fetch('/api/video-info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url })
            });

            const data = await response.json();

            if (response.ok) {
                displayVideoInfo(data);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            showError(error.message);
        } finally {
            hideLoader();
        }
    });

    // معالجة النقر على أزرار التحميل
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('download-btn') || e.target.parentElement.classList.contains('download-btn')) {
            const button = e.target.classList.contains('download-btn') ? e.target : e.target.parentElement;
            const url = videoUrlInput.value.trim();
            const itag = button.dataset.itag;
            const type = button.dataset.type;
            
            startDownload(url, itag, type);
        }
    });

    // تعيين السنة الحالية في التذييل
    document.getElementById('currentYear').textContent = new Date().getFullYear();
});
