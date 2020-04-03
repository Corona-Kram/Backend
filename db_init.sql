CREATE TABLE receivers(
    id serial,
    phone VARCHAR(50),
    PRIMARY KEY id  
);
CREATE INDEX receivers_phone_idx ON receivers (phone);

CREATE TABLE message(
    id serial,
    name name,
    message text,
    receiver serial REFERENCES receivers(id),
    time timestamp default now(),
    PRIMARY KEY id
);
CREATE INDEX message_time_idx ON message(time);
