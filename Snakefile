configfile: "config.yaml"

module placeholder:
    snakefile:
        "scripts/placeholder/Snakefile"


use rule * from placeholder as placeholder_*

rule all:
    input:
        rules.placeholder_all.input,
