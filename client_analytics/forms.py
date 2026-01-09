from django import forms
from django.core.exceptions import ValidationError
from .models import Dataset
from .services.data_processing import process_raw_data
import os
import pandas as pd
from django.core.files.base import ContentFile
from io import BytesIO


class UploadDatasetForm(forms.ModelForm):
    """Form for uploading a new dataset"""
    
    class Meta:
        model = Dataset
        fields = ['name', 'file']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du dataset'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.xlsx,.xls'
            })
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file extension
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in ['.xlsx', '.xls']:
                raise ValidationError("Seuls les fichiers Excel (.xlsx, .xls) sont acceptés.")
            
            # Check file size (10MB max)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError("Le fichier ne doit pas dépasser 10MB.")
        
        return file
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.source_type = 'upload'
        
        # Apply notebook data processing pipeline
        if instance.file:
            print("\n" + "="*80)
            print("🔄 APPLICATION DU TRAITEMENT DES DONNÉES (pipeline du notebook)")
            print("="*80)
            
            try:
                # Read the uploaded file from memory
                uploaded_file = self.cleaned_data['file']
                file_name = uploaded_file.name
                print(f"\n📂 Lecture du fichier: {file_name}")
                
                # Read Excel with skipfooter=2 like in notebook
                uploaded_file.seek(0)  # Reset file pointer
                df = pd.read_excel(uploaded_file, skipfooter=2)
                initial_shape = df.shape
                print(f"   📊 Données initiales: {initial_shape[0]} lignes, {initial_shape[1]} colonnes")
                
                # Apply the complete processing pipeline from notebook
                df_final = process_raw_data(df)
                final_shape = df_final.shape
                print(f"\n✅ TRAITEMENT TERMINÉ")
                print(f"   📊 Données finales: {final_shape[0]} lignes, {final_shape[1]} colonnes")
                print(f"   📉 Données supprimées: {initial_shape[0] - final_shape[0]} lignes ({((initial_shape[0] - final_shape[0]) / initial_shape[0] * 100):.2f}%)")
                
                # Save the processed data to a new file
                output = BytesIO()
                df_final.to_excel(output, index=False, engine='openpyxl')
                output.seek(0)
                
                # Save the processed file
                instance.file.save(
                    file_name,
                    ContentFile(output.read()),
                    save=False
                )
                
                print(f"\n💾 Fichier traité sauvegardé: {file_name}")
                print("="*80 + "\n")
                
            except Exception as e:
                print(f"\n❌ ERREUR lors du traitement: {str(e)}")
                print("="*80 + "\n")
                raise ValidationError(f"Erreur lors du traitement des données: {str(e)}")
        
        if commit:
            instance.save()
        return instance


class SelectDatasetForm(forms.Form):
    """Form for selecting an existing or demo dataset"""
    
    DEMO_CHOICES = [
        ('demo_clients_1.xlsx', 'Dataset Démo 1 - Données Clients Basiques'),
        ('demo_clients_2.xlsx', 'Dataset Démo 2 - Comportement d\'Achat'),
    ]
    
    choice_type = forms.ChoiceField(
        choices=[
            ('existing', 'Datasets Existants'),
            ('demo', 'Datasets Démo'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='demo',
        label='Type de dataset'
    )
    
    existing_dataset = forms.ModelChoiceField(
        queryset=Dataset.objects.all(),
        required=False,
        empty_label="Sélectionner un dataset...",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Dataset existant'
    )
    
    demo_dataset = forms.ChoiceField(
        choices=DEMO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Dataset démo'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        choice_type = cleaned_data.get('choice_type')
        
        if choice_type == 'existing':
            if not cleaned_data.get('existing_dataset'):
                raise ValidationError("Veuillez sélectionner un dataset existant.")
        elif choice_type == 'demo':
            if not cleaned_data.get('demo_dataset'):
                raise ValidationError("Veuillez sélectionner un dataset démo.")
        
        return cleaned_data
