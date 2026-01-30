@echo off
echo ========================================
echo Demarrage du serveur Django
echo ========================================
echo.
cd c:\Users\ngone\OneDrive\Bureau\CEGID\analytics_portal
echo Repertoire: %CD%
echo.
echo Lancement du serveur sur http://127.0.0.1:8000/
echo.
echo Pour acceder a l'analyse mensuelle amelioree:
echo   1. Ouvrir http://127.0.0.1:8000/ dans votre navigateur
echo   2. Charger un dataset
echo   3. Aller dans "Statistiques (Analyse des donnees)"
echo   4. Cliquer sur l'onglet "Mois"
echo.
echo Appuyez sur Ctrl+C pour arreter le serveur
echo.
python manage.py runserver
