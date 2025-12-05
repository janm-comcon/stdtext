import dacy

for model in dacy.models():
    print(model)

dacy.download_model("da_dacy_small_trf-0.2.0")    