```bash
conda create -n agents python=3.11
conda activate agents
conda install -c conda-forge poetry
conda env export --from-history > environment.yml
```

### Create environment from file
```bash
conda env create -f environment.yml
```


### Temas pendientes
```Text
• Implementar Agente que redistribuya casos
• Implementar OCR como tool para mejorar el rendimiento de lectura de pdfs/imagenes
• Implementar manejo de Excepciones: 
    • Contemplar el error "ValueError: Azure has not provided the response due to a content filter being triggered" para ignorar el caso
    por ser contenido que no pasa el filtro de openai.
```