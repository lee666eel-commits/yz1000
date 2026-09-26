# Refresh the Kaggle OAuth access token from the stored refresh_token (kaggle CLI 2.2.4
# does not always do it itself; symptom = every kernels call answers "Permission kernels.get was denied").
from kagglesdk import KaggleClient
from kagglesdk.kaggle_creds import KaggleCredentials
creds = KaggleCredentials.load(KaggleClient())
creds.refresh_access_token()
creds.save()
print("kaggle token refreshed, expires", creds._access_token_expiration)
