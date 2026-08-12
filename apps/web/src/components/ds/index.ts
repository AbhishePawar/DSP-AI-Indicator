/**
 * DSP Design System (EPIC-F001) — shadcn-style primitives mapped to PR1.2 tokens.
 * Pure reusable UI. No business logic. No API calls.
 */

export { Button, buttonVariants, type ButtonProps } from "./forms/button";
export { IconButton, type IconButtonProps } from "./forms/icon-button";
export { Input, type InputProps } from "./forms/input";
export { PasswordInput, type PasswordInputProps } from "./forms/password-input";
export { Textarea, type TextareaProps } from "./forms/textarea";
export {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./forms/select";
export { MultiSelect, type MultiSelectProps } from "./forms/multi-select";
export { Checkbox, type CheckboxProps } from "./forms/checkbox";
export { RadioGroup, RadioGroupItem } from "./forms/radio";
export { Switch, type SwitchProps } from "./forms/switch";
export { Slider, type SliderProps } from "./forms/slider";
export { DatePicker, type DatePickerProps } from "./forms/date-picker";
export { SearchBox, type SearchBoxProps } from "./forms/search-box";
export { FormField, type FormFieldProps } from "./forms/form-field";
export {
  ValidationMessage,
  type ValidationMessageProps,
} from "./forms/validation-message";

export { Badge, type BadgeProps } from "./data/badge";
export { Avatar, AvatarFallback, AvatarImage } from "./data/avatar";
export { Tag, type TagProps } from "./data/tag";
export { Chip, type ChipProps } from "./data/chip";
export {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "./data/tooltip";
export { Popover, PopoverContent, PopoverTrigger } from "./data/popover";
export {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./data/dropdown-menu";
export { Pagination, type PaginationProps } from "./data/pagination";
export { Tabs, TabsContent, TabsList, TabsTrigger } from "./data/tabs";
export {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "./data/accordion";
export {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./data/table";
export { DataGrid, type DataGridProps } from "./data/data-grid";
export { TreeView, type TreeNode, type TreeViewProps } from "./data/tree-view";

export { Container, type ContainerProps } from "./layout/container";
export { Stack, type StackProps } from "./layout/stack";
export { Grid, type GridProps } from "./layout/grid";
export { Flex, type FlexProps } from "./layout/flex";
export { Section, type SectionProps } from "./layout/section";
export {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "./layout/card-layout";
export { PageLayout, type PageLayoutProps } from "./layout/page-layout";

export { Typography, type TypographyProps } from "./typography/typography";

export {
  Sidebar,
  SidebarGroup,
  SidebarItem,
  type SidebarItemProps,
  type SidebarProps,
} from "./navigation/sidebar";
export { Header, type HeaderProps } from "./navigation/header";
export {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbSeparator,
} from "./navigation/breadcrumb";
export {
  CommandPalette,
  type CommandPaletteItem,
  type CommandPaletteProps,
} from "./navigation/command-palette";
export { UserMenu, type UserMenuProps } from "./navigation/user-menu";

export { Alert, type AlertProps } from "./feedback/alert";
export {
  ToastProvider,
  ToastViewport,
  useToast,
} from "./feedback/toast";
export { Progress, type ProgressProps } from "./feedback/progress";
export { Skeleton, type SkeletonProps } from "./feedback/skeleton";
export { Spinner, type SpinnerProps } from "./feedback/spinner";
export { EmptyState, type EmptyStateProps } from "./feedback/empty-state";
export { ErrorState, type ErrorStateProps } from "./feedback/error-state";
export { SuccessState, type SuccessStateProps } from "./feedback/success-state";
export {
  LoadingOverlay,
  type LoadingOverlayProps,
} from "./feedback/loading-overlay";

export {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "./dialogs/modal";
export { Drawer, DrawerContent, DrawerTrigger, type DrawerProps } from "./dialogs/drawer";
export {
  ConfirmationDialog,
  type ConfirmationDialogProps,
} from "./dialogs/confirmation-dialog";
export {
  CommandDialog,
  type CommandDialogProps,
} from "./dialogs/command-dialog";

export { ThemeSwitcher } from "./theme/theme-switcher";
export { DspThemeProvider, useNextTheme } from "./theme/dsp-theme-provider";
export { COMPONENT_CATALOGUE, DESIGN_SYSTEM_VERSION } from "./catalogue";

export { ChartContainer } from "./charts/chart-container";
export { ChartThemeWrapper } from "./charts/chart-theme-wrapper";
export { ResponsiveWrapper } from "./charts/responsive-wrapper";

export { DsIcons } from "./utilities/icons";
export { PermissionWrapper } from "./utilities/permission-wrapper";
export {
  HideBelow,
  ShowAbove,
  useMediaQuery,
} from "./utilities/responsive";
export { useKeyboardShortcut } from "./utilities/keyboard";
export { DsErrorBoundary } from "./utilities/error-boundary";
export { LoadingBlock } from "./utilities/loading";
