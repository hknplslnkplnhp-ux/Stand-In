# FSP Tıbbi Terminoloji Quiz (Streamlit)

Hafif, hızlı ve GPU gerektirmeyen bir quiz uygulaması.

## Özellikler
- PDF/TXT yükleme
- Metinden terim çifti çıkarma
- Çift yönlü quiz:
  - Günlük Almanca → Latince
  - Latince → Günlük Almanca
- Doğru/yanlış kontrolü
- Puan sistemi
- Yanlış yapılan soruları tekrar sorma modu
- Manuel terim listesi ekleme
- Büyük-küçük harf duyarsız ve umlaut toleranslı cevap kontrolü

## Kurulum
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Çalıştırma
```bash
streamlit run app.py
```

## Veri formatı (önerilen)
Her satır bir çift olacak şekilde:

```txt
Halsentzündung / Pharyngitis
Bluthochdruck : Hypertonie
```

Desteklenen ayraçlar: `/`, `|`, `;`, `:`, `->`, `=>`, `=`.

## Örnek dosya
- `sample_data/fsp_terms_sample.txt`

