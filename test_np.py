import numpy as np

y_train = ['positif', 'negatif', 'positif']
try:
    idx = np.where(y_train == 'positif')
    print(f"List comparison idx: {idx}")
except Exception as e:
    print(f"List comparison error: {e}")

y_train_arr = np.array(y_train)
idx_arr = np.where(y_train_arr == 'positif')
print(f"Array comparison idx: {idx_arr}")
