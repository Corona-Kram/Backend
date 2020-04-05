CREATE TABLE receivers(
    phone VARCHAR(50) PRIMARY KEY,
    time timestamp default now(),
    last_sent timestamp default to_timestamp(0),
    active bool default true
);
CREATE INDEX receivers_phone_idx ON receivers (phone);

CREATE TABLE message(
    id serial PRIMARY KEY,
    name name,
    text text,
    receiver VARCHAR(50) REFERENCES receivers(phone),
    time timestamp default now(),
    flag boolean
);
CREATE INDEX message_time_idx ON message(time);
CREATE INDEX message_flag_idx ON message (flag);
