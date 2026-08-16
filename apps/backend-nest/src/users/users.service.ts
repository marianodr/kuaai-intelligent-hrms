import { Injectable, ConflictException, NotFoundException, BadRequestException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import * as bcrypt from 'bcrypt';
import { User, UserRole } from './entities/user.entity';
import { UpdateUserDto } from './dto/update-user.dto';

@Injectable()
export class UsersService {
  constructor(
    @InjectRepository(User) private readonly repo: Repository<User>,
  ) {}

  findByEmail(email: string): Promise<User | null> {
    return this.repo.findOne({ where: { email } });
  }

  findAll(): Promise<Omit<User, 'password'>[]> {
    return this.repo.find({
      select: ['id', 'email', 'role', 'is_active', 'created_at'],
      order: { created_at: 'DESC' },
    });
  }

  async findOne(id: number): Promise<Omit<User, 'password'>> {
    const user = await this.repo.findOne({
      where: { id },
      select: ['id', 'email', 'role', 'is_active', 'created_at'],
    });
    if (!user) throw new NotFoundException(`Usuario ${id} no encontrado`);
    return user;
  }

  async createUser(email: string, password: string, role: UserRole): Promise<Omit<User, 'password'>> {
    const existing = await this.findByEmail(email);
    if (existing) throw new ConflictException('El email ya está registrado');

    const hashed = await bcrypt.hash(password, 10);
    const user = this.repo.create({ email, password: hashed, role });
    const saved = await this.repo.save(user);
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { password: _, ...safe } = saved;
    return safe as Omit<User, 'password'>;
  }

  async updateUser(id: number, dto: UpdateUserDto): Promise<Omit<User, 'password'>> {
    const user = await this.repo.findOne({ where: { id } });
    if (!user) throw new NotFoundException(`Usuario ${id} no encontrado`);

    // Solo hay un admin (creado al bootstrap) y nunca deja de serlo: desde
    // este panel únicamente se le puede cambiar la contraseña.
    if (user.role === 'admin' && (dto.email !== undefined || dto.is_active !== undefined)) {
      throw new BadRequestException(
        'El usuario administrador solo permite cambiar la contraseña desde este panel',
      );
    }

    if (dto.email) user.email = dto.email;
    if (dto.is_active !== undefined) user.is_active = dto.is_active;
    if (dto.password) user.password = await bcrypt.hash(dto.password, 10);

    await this.repo.save(user);
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { password: _, ...safe } = user;
    return safe as Omit<User, 'password'>;
  }

  async deactivateUser(id: number): Promise<Omit<User, 'password'>> {
    return this.updateUser(id, { is_active: false });
  }
}
