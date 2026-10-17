import type { Day, Schedule, Tick } from "./types";

interface Props {
  schedule: Schedule;
  onTick: (tick: Tick) => void;
}

// Week-ahead check, tomorrow's and today's checklists, each item a big tap target.
export default function Checklists({ schedule, onTick }: Props) {
  const { week_check, tomorrow, today } = schedule;
  const hasItems = (d: Day | null) => !!d && d.entries.some((e) => e.items.length > 0);

  return (
    <>
      {week_check && (
        <section>
          <h2>Week ahead {week_check.complete && "· all ready"}</h2>
          <div className="checklist">
            {week_check.items.map((item) => (
              <label key={item.name} className={`tick-row ${item.ticked ? "ticked" : ""}`}>
                <input
                  type="checkbox"
                  checked={item.ticked}
                  onChange={(e) =>
                    onTick({
                      scope: "week",
                      period: week_check.week_start,
                      source: "week",
                      item: item.name,
                      ticked: e.target.checked,
                    })
                  }
                />
                <span>
                  {item.name}
                  <small className="muted"> {item.needed_for.join(", ")}</small>
                </span>
              </label>
            ))}
          </div>
        </section>
      )}

      {hasItems(tomorrow) && tomorrow && <DayChecklist title="Tomorrow" day={tomorrow} onTick={onTick} />}
      {hasItems(today) && <DayChecklist title="Today" day={today} onTick={onTick} />}

      {!week_check && !hasItems(tomorrow) && !hasItems(today) && <p className="muted">Nothing to get ready.</p>}
    </>
  );
}

function DayChecklist({ title, day, onTick }: { title: string; day: Day; onTick: (tick: Tick) => void }) {
  return (
    <section>
      <h2>
        {title} {day.complete && "· all ready"}
      </h2>
      {day.entries
        .filter((entry) => entry.items.length > 0)
        .map((entry) => (
          <div key={entry.source} className="checklist">
            <h3 className="checklist-title">
              {entry.time && <span className="muted">{entry.time} </span>}
              {entry.title}
              {entry.person && <span className="muted"> · {entry.person}</span>}
            </h3>
            {entry.items.map((item) => (
              <label key={item.name} className={`tick-row ${item.ticked ? "ticked" : ""}`}>
                <input
                  type="checkbox"
                  checked={item.ticked}
                  onChange={(e) =>
                    onTick({
                      scope: "day",
                      period: day.day,
                      source: entry.source,
                      item: item.name,
                      ticked: e.target.checked,
                    })
                  }
                />
                <span>{item.name}</span>
              </label>
            ))}
          </div>
        ))}
    </section>
  );
}

// How many items are still unticked in a day.
export function remaining(day: Day | null): number {
  if (!day) return 0;
  return day.entries.reduce((n, e) => n + e.items.filter((i) => !i.ticked).length, 0);
}
