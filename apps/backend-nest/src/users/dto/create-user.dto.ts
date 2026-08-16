import { IsEmail, IsString, MinLength } from 'class-validator';

// Solo se pueden crear usuarios RRHH desde este endpoint. El único admin
// se crea al bootstrap del backend (ver AdminSeeder) a partir de
// ADMIN_EMAIL/ADMIN_PASSWORD.
export class CreateUserDto {
  @IsEmail()
  email: string;

  @IsString()
  @MinLength(8)
  password: string;
}
