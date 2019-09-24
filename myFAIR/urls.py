"""myFAIR URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""

import myFAIR.views as views

from django.conf.urls import url
from django.conf.urls.static import static
from django.conf import settings
from django.views.generic import TemplateView

urlpatterns = [
    url(r'^$', views.index, name="index"),
    url(r'^login', views.login, name="login"),
    url(r'^logout$', views.logout, name="logout"),
    url(r'^upload', views.upload, name="upload"),
    url(r'^triples', views.triples, name="triples"),
    url(r'^samples', views.samples, name="samples"),
    url(r'^delete', TemplateView.as_view(template_name='modify.html'), name="delete"),
    url(r'^results', views.show_results, name="results"),
    url(r'^rerun', views.rerun_analysis, name="rerun"),
    url(r'^investigation', views.investigation, name="investigation"),
    url(r'seek', views.seek, name="seek"),
    url(r'seekupload', views.seekupload, name="seekupload"),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)