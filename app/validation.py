import re
import unicodedata
from datetime import datetime
from typing import Tuple, Dict, Any

AMOUNT_RE = re.compile(r"^\d+(\.\d+)?$")
LOCATION_RE = re.compile(r"^[A-Z]{2}$")
FREQUENCY_RE = re.compile(r"^[1-9]\d*$")
HOUR_RE = re.compile(r"^(0?[0-9]|1[0-9]|2[0-3])[:.][0-5][0-9]$")
CREATION_DATE_RE = re.compile(r"^(0[1-9]|1[0-2])/([0-9]{2})$") 

def normalize_basic(value: str) -> str:
    value = unicodedata.normalize("NFKC", (value or "")).strip()
    return value

def validate_amount(amount: Any) -> Tuple[float, str]:
    if amount is None:
        return 0.0, "No se registro ningun monto :D"
    
    str_amount = normalize_basic(str(amount))
    
    if not AMOUNT_RE.match(str_amount):
        return 0.0, "El monto que se ingreso no es valido. Debe ser un número positivo."
    
    return float(str_amount), ""

def validate_location(location: Any) -> Tuple[str, str]:
    if not location:
        return "", "No se registro ninguna ubicacion :D"
    
    str_loc = normalize_basic(str(location)).upper()
    
    if not LOCATION_RE.match(str_loc):
        return "", "La ubicación debe ser valida. CO para Colombia, US para Estados Unidos, etc."
    
    return str_loc, ""

def validate_frequency(frequency: Any) -> Tuple[int, str]:
    if frequency is None:
        return 1, "No se registro ninguna frecuencia :D"

    str_freq = normalize_basic(str(frequency))
    
    if not FREQUENCY_RE.match(str_freq):
        return 0, "La frecuencia debe ser un número entero mayor o igual a 1."
    
    return int(str_freq), ""

def validate_hour(hour: Any) -> Tuple[int, str]:
    if hour is None:
        return 0, "No se registro ninguna hora :D"

    str_hour = normalize_basic(str(hour))
    
    if not HOUR_RE.match(str_hour):
        return 0, "La hora debe tener un formato de 24 horas con minutos (por ejemplo, 14:30)."
    
    int_hour = int(str_hour.replace(":", ".").split(".")[0])

    return int_hour, ""

def validate_is_new_account(is_new: Any) -> Tuple[bool, str]:
    if is_new is None:
        return False, "No se registro si la cuenta es nueva o no :D"

    str_crea_date = normalize_basic(str(is_new))
    
    if not CREATION_DATE_RE.match(str_crea_date):
        return False, "La fecha de creación debe tener el formato MM/YY."
    
    month = int(str_crea_date[:2])
    year = int(str_crea_date[-2:])

    now = datetime.utcnow()
    antiguedad = (now.year % 100 - year) * 12 + (now.month - month)

    if antiguedad < 0:
        return False, "Verifique la fecha de creación."
    
    return antiguedad, ""

def validate_transaction_data(transaction: dict) -> Tuple[Dict, Dict]:
    clean = {}
    errors = {}

    amt, err = validate_amount(transaction.get("amount"))
    if err: errors["amount"] = err
    clean["amount"] = amt

    loc, err = validate_location(transaction.get("location"))
    if err: errors["location"] = err
    clean["location"] = loc

    freq, err = validate_frequency(transaction.get("frequency", 1))
    if err: errors["frequency"] = err
    clean["frequency"] = freq

    hr, err = validate_hour(transaction.get("hour"))
    if err: errors["hour"] = err
    clean["hour"] = hr

    months, err = validate_is_new_account(transaction.get("creation_date"))
    if err: errors["creation_date"] = err
    clean["creation_date"] = months

    return clean, errors