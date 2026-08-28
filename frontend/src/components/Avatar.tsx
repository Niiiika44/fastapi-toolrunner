import { useState } from "react";

/**
 * A user's picture, with a generated fallback.
 *
 * The fallback is initials on a colour derived from the user id, so two people
 * in the same list never look alike and nothing has to be fetched to draw it.
 * The colour is passed as a custom property and turned into an actual pair of
 * colours in index.css, which is what lets it differ between light and dark.
 */

export interface AvatarSubject {
  id: string;
  first_name: string;
  last_name: string;
  /** Present once the backend serves avatars; carries a ?v= that changes on replace. */
  avatar_url?: string | null;
}

const SIZES = {
  sm: "size-6 text-[0.625rem]",
  md: "size-8 text-xs",
  lg: "size-20 text-2xl",
} as const;

export type AvatarSize = keyof typeof SIZES;

function initials(user: AvatarSubject): string {
  const first = user.first_name.trim().charAt(0);
  const last = user.last_name.trim().charAt(0);
  return `${first}${last}`.toUpperCase() || "?";
}

/** djb2 over the user id — stable across sessions and machines, unlike a random pick. */
function hue(id: string): number {
  let hash = 5381;
  for (let index = 0; index < id.length; index += 1) {
    hash = ((hash << 5) + hash + id.charCodeAt(index)) | 0;
  }
  return Math.abs(hash) % 360;
}

export function Avatar({
  user,
  size = "md",
  className = "",
}: {
  user: AvatarSubject;
  size?: AvatarSize;
  className?: string;
}) {
  // The picture can go missing between render and load — deleted elsewhere, or
  // a storage hiccup. A broken image is worse than the fallback we can draw.
  const [failed, setFailed] = useState(false);
  const name = `${user.first_name} ${user.last_name}`.trim();
  const shape = `${SIZES[size]} shrink-0 rounded-full ${className}`;

  if (user.avatar_url && !failed) {
    return (
      <img
        src={user.avatar_url}
        alt={name}
        onError={() => setFailed(true)}
        className={`${shape} object-cover`}
      />
    );
  }

  return (
    <span
      className={`${shape} avatar-initials inline-flex items-center justify-center font-semibold select-none`}
      style={{ "--avatar-hue": hue(user.id) } as React.CSSProperties}
      // The name is already next to it everywhere it is used; announcing the
      // initials again would just be noise for a screen reader.
      aria-hidden
      title={name}
    >
      {initials(user)}
    </span>
  );
}

/** Avatar and full name on one line — the pairing used in tables and details. */
export function UserChip({
  user,
  size = "sm",
}: {
  user: AvatarSubject;
  size?: AvatarSize;
}) {
  return (
    <span className="inline-flex items-center gap-2">
      <Avatar user={user} size={size} />
      <span className="truncate">{`${user.first_name} ${user.last_name}`.trim()}</span>
    </span>
  );
}
