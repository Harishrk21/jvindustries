import {
  Bell,
  Buildings,
  Camera,
  ChartBar,
  Check,
  ClipboardText,
  DoorOpen,
  Eye,
  EyeSlash,
  FileText,
  Flask,
  GearSix,
  GridFour,
  House,
  IdentificationCard,
  MagnifyingGlass,
  MapPin,
  Package,
  Scales,
  ShieldCheck,
  SignOut,
  Truck,
  ForkKnife,
  WifiHigh,
  WifiSlash,
  Wrench,
  type Icon as PhosphorIcon,
  type IconProps,
} from "@phosphor-icons/react";

/** App icon catalog — [Phosphor Icons](https://phosphoricons.com/) */
const ICONS = {
  home: House,
  truck: Truck,
  scale: Scales,
  file: FileText,
  package: Package,
  search: MagnifyingGlass,
  flask: Flask,
  bell: Bell,
  wrench: Wrench,
  utensils: ForkKnife,
  chart: ChartBar,
  clipboard: ClipboardText,
  offline: WifiSlash,
  online: WifiHigh,
  more: GridFour,
  logout: SignOut,
  shield: ShieldCheck,
  camera: Camera,
  mapPin: MapPin,
  check: Check,
  gate: DoorOpen,
  driver: IdentificationCard,
  plant: Buildings,
  settings: GearSix,
  eye: Eye,
  eyeOff: EyeSlash,
} as const;

export type IconName = keyof typeof ICONS;

type Props = Omit<IconProps, "ref"> & {
  name: IconName;
  /** Phosphor weight — duotone reads well on mobile tiles */
  weight?: IconProps["weight"];
};

export function Icon({ name, size = 22, weight = "duotone", ...rest }: Props) {
  const Cmp: PhosphorIcon = ICONS[name];
  return <Cmp size={size} weight={weight} aria-hidden {...rest} />;
}
