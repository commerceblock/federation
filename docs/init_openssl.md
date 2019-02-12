## init openssl instructions

### gen priv
openssl ecparam -name secp256k1 -genkey -noout -out hsm_priv.pem -engine primus

cat hsm_priv.pem
-----BEGIN EC PRIVATE KEY-----
MHQCAQEEIP/qhE1f7UPgHG9t8XOB5kn1XtpZKLQM32XpsZpgvzHsoAcGBSuBBAAK
oUQDQgAEvrRVpKr4bZxFQ8IcdsXF5Um0fOeirpFsoF0k3asFUsWcg/1OxrAFCcbX
wJCT9jjPDy1b17YKjwx1szWnpJZhUw==

### get pub
openssl ec -in hsm_priv.pem -pubout -out hsm_pub.pem -engine primus

cat hsm_pub.pem
-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAEvrRVpKr4bZxFQ8IcdsXF5Um0fOeirpFs
oF0k3asFUsWcg/1OxrAFCcbXwJCT9jjPDy1b17YKjwx1szWnpJZhUw==
-----END PUBLIC KEY-----

### get pub bytes
openssl ec -in hsm_priv.pem -text -noout -engine primus

Private-Key: (256 bit)
priv:
    00:ff:ea:84:4d:5f:ed:43:e0:1c:6f:6d:f1:73:81:
    e6:49:f5:5e:da:59:28:b4:0c:df:65:e9:b1:9a:60:
    bf:31:ec
pub:
    04:be:b4:55:a4:aa:f8:6d:9c:45:43:c2:1c:76:c5:
    c5:e5:49:b4:7c:e7:a2:ae:91:6c:a0:5d:24:dd:ab:
    05:52:c5:9c:83:fd:4e:c6:b0:05:09:c6:d7:c0:90:
    93:f6:38:cf:0f:2d:5b:d7:b6:0a:8f:0c:75:b3:35:
    a7:a4:96:61:53
ASN1 OID: secp256k1

openssl ec -in hsm_pub.pem -text -pubin -noout

read EC key
Private-Key: (256 bit)
pub:
    04:0c:33:23:f0:64:99:df:64:cb:97:e0:e9:06:85:
    c7:64:0a:31:10:69:39:76:93:61:35:a5:e9:41:b1:
    92:7e:26:f8:02:3d:30:72:f4:d6:39:33:66:4a:0d:
    33:87:1c:a4:ae:83:9b:14:6f:30:a8:c8:6b:f0:d6:
    a2:e4:51:3c:a5
ASN1 OID: secp256k1

openssl ec -in hsm_pub.pem -text -pubin -noout -conv_form compressed

read EC key
Private-Key: (256 bit)
pub:
    03:0c:33:23:f0:64:99:df:64:cb:97:e0:e9:06:85:
    c7:64:0a:31:10:69:39:76:93:61:35:a5:e9:41:b1:
    92:7e:26
ASN1 OID: secp256k1

grep '[a-f0-9]\{2\}[:]\{1\}' file | tr -d [:space:] | sed s/://g | sed '$a\'

### signing

#### sign
openssl dgst -sha256 -sign hsm_priv_1.pem -out eleos.txt.sha256 -keyform ENGINE -engine primus eleos.txt

#### verify
openssl dgst -sha256 -verify hsm_pub_1.pem -signature eleos.txt.sha256 eleos.txt

#### get base64 sig
base64 eleos.txt.sha256 > eleos.txt.sha256.txt
cat eleos.txt.sha256.txt
