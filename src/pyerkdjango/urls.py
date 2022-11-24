from django.urls import path, re_path

from . import views

urlpatterns = [
    path("", views.home_page_view, name="landingpage"),
    path(r"mockup", views.mockup, name="mockuppage"),
    path(r"search/", views.get_item, name="search"),
    path(r"api/get_auto_complete_list", views.get_auto_complete_list, name="get_auto_complete_list"),
    path(r"api/save_file", views.ApiSaveFile.as_view(), name="save_file"),
    path(r"editor", views.EditorView.as_view(), name="show_editor"),
    path(r"reload/", views.reload_data_redirect, name="reload"),
    path("sparql/", views.SearchSparqlView.as_view(), name="sparqlpage"),
    path(r"e/<str:uri>", views.entity_view, name="entitypage"),
    path(r"e/<str:uri>/v", views.entity_visualization_view, name="entityvisualization"),
    path(r"debug", views.debug_view, name="debugpage0"),
    path(r"debug/<int:xyz>", views.debug_view, name="debugpage_with_argument"),
]
