from pysaic.enums import FactionsEnum

crcr_factions = {
    FactionsEnum.Military.value: 16,
    FactionsEnum.Bandit.value: 18,
    FactionsEnum.Clear_Sky.value: 20,
    FactionsEnum.Duty.value: 10,
    FactionsEnum.Ecologist.value: 7,
    FactionsEnum.Freedom.value: 16,
    FactionsEnum.SIN.value: 8,
    FactionsEnum.UNISG.value: 10,
    FactionsEnum.Mercenary.value: 14,
    FactionsEnum.Monolith.value: 8,
    FactionsEnum.Renegade.value: 10,
    FactionsEnum.Loner.value: 20,
    FactionsEnum.Zombie.value: 18,
}

pysaic_factions = {
    FactionsEnum.Military.value: 35,
    FactionsEnum.Bandit.value: 42,
    FactionsEnum.Clear_Sky.value: 43,
    FactionsEnum.Duty.value: 43,
    FactionsEnum.Ecologist.value: 40,
    FactionsEnum.Freedom.value: 45,
    FactionsEnum.SIN.value: 35,
    FactionsEnum.UNISG.value: 33,
    FactionsEnum.Mercenary.value: 44,
    FactionsEnum.Monolith.value: 35,
    FactionsEnum.Renegade.value: 33,
    FactionsEnum.Loner.value: 57,
    FactionsEnum.Zombie.value: 0,
}

FACTION_AVATARS = {
    "Military": crcr_factions[FactionsEnum.Military.value]
    + pysaic_factions[FactionsEnum.Military.value],
    "Bandit": crcr_factions[FactionsEnum.Bandit.value]
    + pysaic_factions[FactionsEnum.Bandit.value],
    "Clear Sky": crcr_factions[FactionsEnum.Clear_Sky.value]
    + pysaic_factions[FactionsEnum.Clear_Sky.value],
    "Clear_Sky": crcr_factions[FactionsEnum.Clear_Sky.value]
    + pysaic_factions[FactionsEnum.Clear_Sky.value],
    "Duty": crcr_factions[FactionsEnum.Duty.value]
    + pysaic_factions[FactionsEnum.Duty.value],
    "Ecologist": crcr_factions[FactionsEnum.Ecologist.value]
    + pysaic_factions[FactionsEnum.Ecologist.value],
    "Freedom": crcr_factions[FactionsEnum.Freedom.value]
    + pysaic_factions[FactionsEnum.Freedom.value],
    "SIN": crcr_factions[FactionsEnum.SIN.value]
    + pysaic_factions[FactionsEnum.SIN.value],
    "UNISG": crcr_factions[FactionsEnum.UNISG.value]
    + pysaic_factions[FactionsEnum.UNISG.value],
    "Mercenary": crcr_factions[FactionsEnum.Mercenary.value]
    + pysaic_factions[FactionsEnum.Mercenary.value],
    "Monolith": crcr_factions[FactionsEnum.Monolith.value]
    + pysaic_factions[FactionsEnum.Monolith.value],
    "Renegade": crcr_factions[FactionsEnum.Renegade.value]
    + pysaic_factions[FactionsEnum.Renegade.value],
    "Loner": crcr_factions[FactionsEnum.Loner.value]
    + pysaic_factions[FactionsEnum.Loner.value],
    "Zombies": crcr_factions[FactionsEnum.Zombie.value]
    + pysaic_factions[FactionsEnum.Zombie.value],
}
