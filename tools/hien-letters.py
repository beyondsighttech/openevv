#!/usr/bin/env python3
"""Write hien's letter rules: one per Devanagari character.

A letter rule names the sound it lays down by address, and an address is a
symbol fixed at compile time -- `insert_2pt_s 2 1 sym hi_k 0'. There is no
operation that reads a letter's own phoneme field and lays that down, so one
rule cannot serve every consonant: Italian has twenty-six letter rules and
Polish fifteen, each naming its own sounds. Hindi wants forty-four, and writing
forty-four rules by hand that differ in two symbols each is how one of them
quietly gets the wrong sound.

So this writes them. The shape is one rule, stated once below, and the only
things that vary are the letter's name and its two strings -- bare, and with the
inherent a. What that buys beyond typing is that a change to the shape is a
change in one place: the schwa-deletion arm was wrong in the first version and
fixing it fixed all thirty-three consonants at once.

Devanagari is an abugida, which is what the shape is about. A consonant is a
consonant and the vowel a together, so क on its own is `ka' and never `k'.
Three things override that, and the rule asks in this order:

  a virama next     क्ष  -- no vowel at all, and the cluster's second
                            consonant carries the a
  a vowel sign next का   -- the sign's vowel instead of the a
  end of the word   राम  -- Hindi deletes a word-final inherent a, so this is
                            raam and not raama

Order matters between the first two: both eat the character after the
consonant, and a virama is not a vowel sign, so whichever is asked first has to
be the one that is there.

usage: hien-letters.py [--dry-run]
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "lang", "hien", "rules", "hien_lts.up")

#: Every consonant: the name its alphabet slot has, the symbol for the bare
#: sound and the symbol for the sound with the inherent a. The comment is what
#: the letter is, in transliteration, since a terminal may have no Devanagari.
CONSONANTS = [
    ("dka",   "hi_k",    "hi_ka",    "ka"),
    ("dkha",  "hi_kh",   "hi_kha",   "kha"),
    ("dga",   "hi_g",    "hi_ga",    "ga"),
    ("dgha",  "hi_gh",   "hi_gha",   "gha"),
    ("dnga",  "hi_ng",   "hi_nga",   "nga"),
    ("dca",   "hi_c",    "hi_ca",    "ca"),
    ("dcha",  "hi_ch",   "hi_cha",   "cha"),
    ("dja",   "hi_j",    "hi_ja",    "ja"),
    ("djha",  "hi_jh",   "hi_jha",   "jha"),
    ("dnya",  "hi_ny",   "hi_nya",   "nya"),
    ("dTa",   "hi_tt",   "hi_tta",   "Ta"),
    ("dTha",  "hi_tth",  "hi_ttha",  "Tha"),
    ("dDa",   "hi_dd",   "hi_dda",   "Da"),
    ("dDha",  "hi_ddh",  "hi_ddha",  "Dha"),
    ("dNa",   "hi_nn",   "hi_nna",   "Na"),
    ("dta",   "hi_t",    "hi_ta",    "ta"),
    ("dtha",  "hi_th",   "hi_tha",   "tha"),
    ("dda",   "hi_d",    "hi_da",    "da"),
    ("ddha",  "hi_dh",   "hi_dha",   "dha"),
    ("dna",   "hi_n",    "hi_na",    "na"),
    ("dpa",   "hi_p",    "hi_pa",    "pa"),
    ("dpha",  "hi_ph",   "hi_pha",   "pha"),
    ("dba",   "hi_b",    "hi_ba",    "ba"),
    ("dbha",  "hi_bh",   "hi_bha",   "bha"),
    ("dma",   "hi_m",    "hi_ma",    "ma"),
    ("dya",   "hi_y",    "hi_ya",    "ya"),
    ("dra",   "hi_r",    "hi_ra",    "ra"),
    ("dla",   "hi_l",    "hi_la",    "la"),
    ("dva",   "hi_v",    "hi_va",    "va"),
    ("dsha",  "hi_sh",   "hi_sha",   "sha"),
    ("dSha",  "hi_ssh",  "hi_ssha",  "Sha"),
    ("dsa",   "hi_s",    "hi_sa",    "sa"),
    ("dha",   "hi_h",    "hi_ha",    "ha"),
]

#: The independent vowels and the signs. One sound each and nothing after them
#: changes it, so these are the simple shape.
VOWELS = [
    ("da_",   "hi_a",    "a"),
    ("daa",   "hi_aa",   "aa"),
    ("di",    "hi_i",    "i"),
    ("dii",   "hi_ii",   "ii"),
    ("du",    "hi_u",    "u"),
    ("duu",   "hi_uu",   "uu"),
    ("dri",   "hi_ri",   "ri"),
    ("de",    "hi_e",    "e"),
    ("dai",   "hi_ai",   "ai"),
    ("do",    "hi_o",    "o"),
    ("dau",   "hi_au",   "au"),
    ("danu",  "hi_anu",  "anusvara"),
    ("dvisarga", "hi_visg", "visarga"),
]

HEAD = '''# What a Devanagari letter says. Written by tools/hien-letters.py.
#
# This is the rule the module exists for. Everything before it -- the alphabet,
# the code point table, the widened records -- only got the letters to arrive;
# nothing said what any of them sounds like, so every word came out as the same
# default noise. This is what turns a letter into a sound.
#
# The shape is English's and Italian's, because it is the machine's. A letter
# rule is handed the two ends of the run of characters it is asked about, and it
# puts phoneme codes between them: lpta and rpta are those ends and
# insert_2pt_s fills the range. A rule that reads more than one character moves
# the right-hand end past the extra ones -- savescptr puts where the scan has
# got to into the cell -- and answers that position through the second pointer,
# so the next character read is the one after what this rule consumed.
#
# Devanagari is an abugida, which is why every consonant rule has four arms. A
# consonant is a consonant and the vowel a together: क is `ka' and never `k'.
# Three things override that -- a virama, a vowel sign, or the end of the word,
# which in Hindi deletes the inherent a. राम is raam, not raama.
#
# The sounds are lang/hien/rules/constants, and eighteen of the letters are
# pointed at an approximate one: the aspirates say the unaspirated sound and the
# retroflex series says the dental, because a phoneme code that never existed is
# invisible to the five hundred places a module tests one by name.
# lang/hien/hien.repointed records which. Fixing those is a phoneme question and
# changes the constants file, not this one.
#
# DO NOT EDIT. tools/hien-letters.py writes it; edit the shape there and every
# letter gets the fix at once, which is the point -- the schwa arm was wrong in
# the first version and one edit fixed all thirty-three.

'''

CONSONANT = '''# %(what)s
rule hi_letter_%(name)s takes 3 from hien_lts.obj
  local left bytes 8
  local right bytes 8
  call ZZget_parm_ptr2 addr left arg 1 addr right arg 2
  call ZZfence_null

  # A virama next? Then no vowel at all, and this is a cluster.
  plant test %(name)s_sign
  call ZZlpta_load__setscan_nof_r__1 addr right
  if answer is 0
    call hi_is_virama
    if answer is 0
      call savescptr 1 addr right
      call lpta_rpta_loadp addr left addr right
      call insert_2pt_s 2 1 sym %(bare)s 0
      if answer is 0
        go to %(name)s_said
      end
    end
  end
  backtrack

place %(name)s_sign
  # A vowel sign next? Then its vowel instead of the inherent a. The sign is
  # eaten with the consonant, and the sign's own rule lays the vowel down.
  plant test %(name)s_final
  call ZZlpta_load__setscan_nof_r__1 addr right
  if answer is 0
    call hi_is_matra
    if answer is 0
      call lpta_rpta_loadp addr left addr right
      call insert_2pt_s 2 1 sym %(bare)s 0
      if answer is 0
        go to %(name)s_said
      end
    end
  end
  backtrack

place %(name)s_final
  # The end of the word? Then the inherent a is not spoken.
  plant test %(name)s_plain
  call ZZlpta_load__setscan_nof_r__1 addr right
  if answer is not 0
    call lpta_rpta_loadp addr left addr right
    call insert_2pt_s 2 1 sym %(bare)s 0
    if answer is 0
      go to %(name)s_said
    end
  end
  backtrack

place %(name)s_plain
  # And otherwise the consonant carries its a, which is every syllable in the
  # middle of a word.
  call lpta_rpta_loadp addr left addr right
  call insert_2pt_s 2 2 sym %(with_a)s 0
  if answer is not 0
    give up
  end

place %(name)s_said
  call succeed
  put cell right value into arg 2 at 4
  answer 0
end

'''

VOWEL = '''# %(what)s
rule hi_letter_%(name)s takes 3 from hien_lts.obj
  local left bytes 8
  local right bytes 8
  call ZZget_parm_ptr2 addr left arg 1 addr right arg 2
  call ZZfence_null
  call lpta_rpta_loadp addr left addr right
  call insert_2pt_s 2 %(n)d sym %(sound)s 0
  if answer is not 0
    give up
  end
  call succeed
  put cell right value into arg 2 at 4
  answer 0
end

'''

HELPERS = '''# ---------------------------------------------------------------------------
# Is the character the scan is on a virama, or a vowel sign?
#
# Both are one test against one character code, and both are asked by every
# consonant rule, so they are rules of their own rather than thirty-three
# copies. `bare' because they stand where a wrapper stands: the choice points
# around the call belong to the rule that planted them, and a succeed here
# would commit them.
rule hi_is_virama takes 1 from hien_lts.obj
  bare
  call ZZtest_string_s_1_1_hi_virama_char
  answer answer
end

rule hi_is_matra takes 1 from hien_lts.obj
  bare
  call ZZtest_string_s_1_1_hi_matra_chars
  answer answer
end
'''


def main(argv):
    out = [HEAD]
    for name, bare, with_a, what in CONSONANTS:
        out.append(CONSONANT % {"name": name, "bare": bare,
                                "with_a": with_a, "what": what})
    for name, sound, what in VOWELS:
        # ri is two codes, r then i; every other vowel is one.
        n = 2 if sound == "hi_ri" else 1
        out.append(VOWEL % {"name": name, "sound": sound, "what": what,
                            "n": n})
    out.append(HELPERS)

    body = "".join(out)
    if "--dry-run" in argv:
        print(body[:2000])
        print("... %d bytes, %d rules"
              % (len(body), body.count("\nrule ") + 1))
        return 0

    open(OUT, "w", newline="\n").write(body)
    print("wrote %s: %d rules, %d bytes"
          % (os.path.relpath(OUT, ROOT), body.count("\nrule ") + 1, len(body)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
