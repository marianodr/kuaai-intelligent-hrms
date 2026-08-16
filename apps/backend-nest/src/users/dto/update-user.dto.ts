import { IsBoolean, IsEmail, IsOptional, IsString, MinLength } from 'class-validator';

// El rol no es editable: el único admin se crea al bootstrap y nunca cambia
// de rol; los usuarios creados desde este panel son siempre RRHH.
export class UpdateUserDto {
  @IsOptional()
  @IsEmail()
  email?: string;

  @IsOptional()
  @IsString()
  @MinLength(8)
  password?: string;

  @IsOptional()
  @IsBoolean()
  is_active?: boolean;
}
