from enum import Enum


class IndianState(str, Enum):
    """
    All 28 Indian States and 8 Union Territories.

    Used for validating the `state` field in CrimeLocation.
    Reusable by the frontend for dropdown menus and filter components.

    Reference: Government of India official list of states and UTs.
    """

    # -------------------------------------------------------------------------
    # 28 States
    # -------------------------------------------------------------------------
    ANDHRA_PRADESH = "Andhra Pradesh"
    ARUNACHAL_PRADESH = "Arunachal Pradesh"
    ASSAM = "Assam"
    BIHAR = "Bihar"
    CHHATTISGARH = "Chhattisgarh"
    GOA = "Goa"
    GUJARAT = "Gujarat"
    HARYANA = "Haryana"
    HIMACHAL_PRADESH = "Himachal Pradesh"
    JHARKHAND = "Jharkhand"
    KARNATAKA = "Karnataka"
    KERALA = "Kerala"
    MADHYA_PRADESH = "Madhya Pradesh"
    MAHARASHTRA = "Maharashtra"
    MANIPUR = "Manipur"
    MEGHALAYA = "Meghalaya"
    MIZORAM = "Mizoram"
    NAGALAND = "Nagaland"
    ODISHA = "Odisha"
    PUNJAB = "Punjab"
    RAJASTHAN = "Rajasthan"
    SIKKIM = "Sikkim"
    TAMIL_NADU = "Tamil Nadu"
    TELANGANA = "Telangana"
    TRIPURA = "Tripura"
    UTTAR_PRADESH = "Uttar Pradesh"
    UTTARAKHAND = "Uttarakhand"
    WEST_BENGAL = "West Bengal"

    # -------------------------------------------------------------------------
    # 8 Union Territories
    # -------------------------------------------------------------------------
    ANDAMAN_AND_NICOBAR_ISLANDS = "Andaman and Nicobar Islands"
    CHANDIGARH = "Chandigarh"
    DADRA_AND_NAGAR_HAVELI_AND_DAMAN_AND_DIU = (
        "Dadra and Nagar Haveli and Daman and Diu"
    )
    DELHI = "Delhi"
    JAMMU_AND_KASHMIR = "Jammu and Kashmir"
    LADAKH = "Ladakh"
    LAKSHADWEEP = "Lakshadweep"
    PUDUCHERRY = "Puducherry"
