import { IsString, IsEmail, IsOptional, MinLength } from 'class-validator';

export class CreateEmployeeDto {
  @IsString()
  first_name: string;

  @IsString()
  last_name: string;

  @IsEmail()
  @IsOptional()
  email?: string;

  @IsString()
  @MinLength(1)
  legajo: string;

  @IsString()
  @MinLength(1)
  rfid_code: string;

  @IsString()
  @IsOptional()
  department?: string;
}
