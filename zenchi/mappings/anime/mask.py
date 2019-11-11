# byte 1
aid = 1 << 7 << 48
date_flags = 1 << 6 << 48
year = 1 << 5 << 48
type = 1 << 4 << 48
related_aid_list = 1 << 3 << 48
related_aid_type = 1 << 2 << 48

# byte 2
romaji_name = 1 << 7 << 40
kanji_name = 1 << 6 << 40
english_name = 1 << 5 << 40
other_name = 1 << 4 << 40
short_name = 1 << 3 << 40
synonym_list = 1 << 2 << 40

# byte 3
episodes = 1 << 7 << 32
highest_episode_number = 1 << 6 << 32
special_ep_count = 1 << 5 << 32
air_date = 1 << 4 << 32
end_date = 1 << 3 << 32
url = 1 << 2 << 32
picname = 1 << 1 << 32

# byte 4
rating = 1 << 7 << 24
vote_count = 1 << 6 << 24
temp_rating = 1 << 5 << 24
temp_vote = 1 << 4 << 24
averate_view_rating = 1 << 3 << 24
review_count = 1 << 2 << 24
award_list = 1 << 1 << 24
is_18_restricted = 1 << 24

# byte 5
ann_id = 1 << 6 << 16
allcinema_id = 1 << 5 << 16
anime_nfo_id = 1 << 4 << 16
tag_name_list = 1 << 3 << 16
tag_id_list = 1 << 2 << 16
tag_weight_list = 1 << 1 << 16
date_record_updated = 1 << 16

# byte 6
character_id_list = 1 << 7 << 8

# byte 7
specials_count = 1 << 7
credits_count = 1 << 6
other_count = 1 << 5
trailer_count = 1 << 4
parody_count = 1 << 3
